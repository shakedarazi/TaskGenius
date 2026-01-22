def _build_prompt(self, request: ChatRequest) -> str:
        """
        Build prompt for LLM based on user message and context.
        
        Args:
            request: Chat request with message and context data
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are a helpful assistant for TaskGenius, a task management system.",
            "",
            "YOUR ROLE:",
            "- Help users manage their tasks by understanding their intent",
            "- Ask for clarification when information is missing or ambiguous",
            "- Refer to specific tasks when relevant (use task titles, deadlines, priorities)",
            "- Be aware of task context: deadlines, priorities, statuses",
            "- NEVER assume or guess - always ask if unclear",
            "- REMEMBER previous conversation context - users may continue previous requests",
            "",
        ]
        
        # Add conversation history if available
        if request.conversation_history:
            prompt_parts.append("CONVERSATION HISTORY (IMPORTANT - USE THIS CONTEXT):")
            # Limit to last 10 messages to avoid token limits
            recent_history = request.conversation_history[-10:]
            
            # Check if last assistant message was a completion confirmation
            last_assistant_was_completion = False
            if recent_history:
                last_msg = recent_history[-1]
                if last_msg.get("role") == "assistant":
                    last_content = last_msg.get("content", "").lower()
                    # Check for completion indicators
                    completion_indicators = [
                        "✅", "הוספתי", "עדכנתי", "מחקתי", "added", "updated", "deleted",
                        "created", "completed", "done", "finished", "successfully"
                    ]
                    if any(indicator in last_content for indicator in completion_indicators):
                        last_assistant_was_completion = True
            
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            prompt_parts.append("")
            
            if last_assistant_was_completion:
                prompt_parts.append("⚠️ CRITICAL: The last assistant message was a COMPLETION CONFIRMATION (task was added/updated/deleted).")
                prompt_parts.append("This means the previous transaction is FINISHED. The user's current message is likely a NEW request.")
                prompt_parts.append("DO NOT continue the old transaction. Treat the user's current message as a fresh start.")
                prompt_parts.append("If the user asks a new question or wants to do something different, respond to the NEW request.")
                prompt_parts.append("IMPORTANT: When answering questions about tasks, use the CURRENT TASKS LIST above (from database), NOT the conversation history.")
                prompt_parts.append("The tasks list is always up-to-date and reflects the current state after the completed operation.")
                prompt_parts.append("Only use the conversation history for general context, NOT to continue the completed transaction or to get task data.")
                prompt_parts.append("")
            else:
                prompt_parts.append("CRITICAL: The user's current message may be a continuation of the conversation above.")
                prompt_parts.append("For example, if you asked 'What priority?' and the user responds 'medium', they are answering your question.")
                prompt_parts.append("Extract information from BOTH the current message AND the conversation history.")
                prompt_parts.append("")
                prompt_parts.append("IMPORTANT: When answering questions about tasks (e.g., 'what tasks do I have?', 'what's due tomorrow?'),")
                prompt_parts.append("ALWAYS use the CURRENT TASKS LIST above (from database), NOT the conversation history.")
                prompt_parts.append("The tasks list is always the most up-to-date source of truth.")
                prompt_parts.append("")
        
        prompt_parts.append(f"User's CURRENT message: {request.message}")
        prompt_parts.append("")
        
        # Add tasks context
        if request.tasks:
            prompt_parts.append("=" * 50)
            prompt_parts.append("CURRENT USER TASKS (ALWAYS UP-TO-DATE - USE THIS DATA, NOT HISTORY):")
            prompt_parts.append("=" * 50)
            prompt_parts.append("⚠️ CRITICAL: The tasks listed below are ALWAYS the most current data from the database.")
            prompt_parts.append("If the conversation history mentions tasks that differ from this list, TRUST THIS LIST.")
            prompt_parts.append("After a task is created/updated/deleted, this list reflects the current state.")
            prompt_parts.append("When answering questions about tasks, ALWAYS use this list, not the conversation history.")
            prompt_parts.append("")
            for task in request.tasks[:10]:  # Limit to 10 tasks
                title = task.get("title", "Untitled")
                status = task.get("status", "unknown")
                priority = task.get("priority", "unknown")
                deadline = task.get("deadline", "No deadline")
                task_id = task.get("id", "unknown")
                prompt_parts.append(f"  - {title} (ID: {task_id}, Status: {status}, Priority: {priority}, Deadline: {deadline})")
            if len(request.tasks) > 10:
                prompt_parts.append(f"  ... and {len(request.tasks) - 10} more tasks")
            prompt_parts.append("")
            prompt_parts.append("IMPORTANT: When the user mentions tasks, refer to them by title from THIS LIST. If they mention 'tomorrow', 'urgent', 'high priority', etc., filter the tasks from THIS LIST accordingly.")
            prompt_parts.append("=" * 50)
            prompt_parts.append("")
        else:
            prompt_parts.append("User's tasks: None (user has no tasks yet)")
            prompt_parts.append("")
        
        # Add weekly summary if available
        if request.weekly_summary:
            summary = request.weekly_summary
            prompt_parts.append("Weekly summary:")
            completed = summary.get("completed", {}).get("count", 0)
            high_priority = summary.get("high_priority", {}).get("count", 0)
            upcoming = summary.get("upcoming", {}).get("count", 0)
            overdue = summary.get("overdue", {}).get("count", 0)
            prompt_parts.append(f"  - Completed: {completed}")
            prompt_parts.append(f"  - High priority: {high_priority}")
            prompt_parts.append(f"  - Upcoming: {upcoming}")
            prompt_parts.append(f"  - Overdue: {overdue}")
            prompt_parts.append("")
        
        prompt_parts.append("INTENT DETECTION & CLARIFICATION RULES:")
        prompt_parts.append("- If user wants to CREATE a task but didn't provide title → ask: 'What task would you like to create? Please provide a title.'")
        prompt_parts.append("- If user wants to UPDATE/DELETE but task is ambiguous (e.g., 'tomorrow's task' when multiple exist) → list the matching tasks and ask which one")
        prompt_parts.append("- If user mentions urgency/priority/deadline but it's unclear → ask for clarification")
        prompt_parts.append("- If user asks about 'urgent' or 'high priority' tasks → refer to actual high-priority tasks from the list above")
        prompt_parts.append("- If user asks 'what's due' or 'what's coming' → refer to tasks with upcoming deadlines")
        prompt_parts.append("- NEVER guess or assume - always ask if information is missing or ambiguous")
        prompt_parts.append("")
        prompt_parts.append("INTENT TYPES (use these in your reasoning):")
        prompt_parts.append("- 'list_tasks' - user wants to see their tasks")
        prompt_parts.append("- 'task_insights' - user wants insights about tasks (deadlines, priorities, urgency)")
        prompt_parts.append("- 'potential_create' - user wants to create a task but information is incomplete")
        prompt_parts.append("- 'potential_delete' - user wants to delete a task but target is unclear")
        prompt_parts.append("")
        prompt_parts.append("OUTPUT FORMAT (Phase 3 - Structured Output):")
        prompt_parts.append("You must respond with TWO SEPARATE parts:")
        prompt_parts.append("1. A natural conversational reply (for the user) - NO JSON, NO CODE, ONLY NATURAL TEXT")
        prompt_parts.append("2. A JSON command object (for the system)")
        prompt_parts.append("")
        prompt_parts.append("Format your response EXACTLY as:")
        prompt_parts.append("REPLY: [your natural conversational response - ONLY TEXT, NO JSON, NO CODE]")
        prompt_parts.append("COMMAND: [JSON object with command structure]")
        prompt_parts.append("")
        prompt_parts.append("CRITICAL OUTPUT RULES:")
        prompt_parts.append("- The REPLY section MUST contain ONLY natural conversational text")
        prompt_parts.append("- DO NOT include JSON, code blocks, or any structured data in the REPLY section")
        prompt_parts.append("- DO NOT repeat the command structure in the REPLY section")
        prompt_parts.append("- The REPLY is what the user will see - keep it clean and natural")
        prompt_parts.append("- The COMMAND section is separate and only for the system")
        prompt_parts.append("- If you include JSON in REPLY, it will confuse the user - NEVER do this")
        prompt_parts.append("")
        prompt_parts.append("COMMAND JSON Structure:")
        prompt_parts.append("{")
        prompt_parts.append('  "intent": "add_task|update_task|delete_task|complete_task|list_tasks|clarify",')
        prompt_parts.append('  "confidence": 0.0-1.0,  // High (>=0.8) only when all required fields are clear')
        prompt_parts.append('  "fields": {  // For add_task: title, priority, deadline, etc.')
        prompt_parts.append('    "title": "string or null",')
        prompt_parts.append('    "priority": "low|medium|high|urgent or null",')
        prompt_parts.append('    "deadline": "ISO date string or null"')
        prompt_parts.append('  },')
        prompt_parts.append('  "ref": {  // For update/delete/complete: task reference')
        prompt_parts.append('    "task_id": "string or null",')
        prompt_parts.append('    "title": "string or null"  // For matching')
        prompt_parts.append('  },')
        prompt_parts.append('  "ready": true/false,  // true only when all required fields are present')
        prompt_parts.append('  "missing_fields": ["field1", "field2"]  // List missing required fields')
        prompt_parts.append("}")
        prompt_parts.append("")
        prompt_parts.append("DATE/DEADLINE HANDLING RULES (CRITICAL - MUST FOLLOW):")
        prompt_parts.append("- When user provides a date/deadline, try to understand it (e.g., 'tomorrow', 'יום רביעי', '20.1', '2024-01-20')")
        prompt_parts.append("- If user says 'no', 'none', 'אין', or 'לא' when asked about deadline → set deadline to null (no deadline)")
        prompt_parts.append("- CRITICAL: If user provides ANYTHING ELSE that is NOT 'no'/'none'/'אין'/'לא' AND is NOT a clear, valid date,")
        prompt_parts.append("  DO NOT guess or use default dates. DO NOT use old dates (e.g., 2023, 25/10/2023).")
        prompt_parts.append("  DO NOT try to interpret unclear text as a date.")
        prompt_parts.append("  Instead, in your REPLY, ask the user: 'אנא תן תאריך במספרים (למשל: 2024-01-20 או 20.1.2024), או כתוב 'לא' אם אין תאריך יעד'")
        prompt_parts.append("  (or in English: 'Please provide a date in numbers (e.g., 2024-01-20 or 20.1.2024), or write 'no' if there's no deadline')")
        prompt_parts.append("  In the COMMAND, set deadline to null and set ready=false with 'deadline' in missing_fields.")
        prompt_parts.append("- NEVER use dates from years ago (e.g., 2023, 25/10/2023) - these are invalid and will be rejected by the system.")
        prompt_parts.append("- NEVER use default/placeholder dates - only use dates explicitly provided by the user in a clear format.")
        prompt_parts.append("- Example: If user says 'יום רביעי' and you're not sure which Wednesday, ask: 'איזה יום רביעי? אנא תן תאריך במספרים (למשל: 20.1.2024)'")
        prompt_parts.append("- Example: If user says 'tomorrow' but context is unclear, ask: 'What date is tomorrow? Please provide the date in numbers (e.g., 2024-01-20)'")
        prompt_parts.append("- Example: If user writes something unclear like 'maybe next week' or 'I don't know' (not 'no'/'none' and not a clear date),")
        prompt_parts.append("  ask: 'אנא תן תאריך במספרים (למשל: 2024-01-20), או כתוב 'לא' אם אין תאריך יעד'")
        prompt_parts.append("  (or in English: 'Please provide a date in numbers (e.g., 2024-01-20), or write 'no' if there's no deadline')")
        prompt_parts.append("")
        prompt_parts.append("RULES FOR COMMAND GENERATION:")
        prompt_parts.append("- For 'add_task': Set ready=true ONLY if BOTH title AND priority are provided. confidence>=0.8 only if both are clear.")
        prompt_parts.append("  REQUIRED FIELDS for add_task: title (mandatory), priority (mandatory), deadline (optional - ask but can be null)")
        prompt_parts.append("  WORKFLOW (MUST FOLLOW THIS ORDER - ONE STEP AT A TIME):")
        prompt_parts.append("    1) FIRST: Ask for title ONLY (e.g., 'What task would you like to create? Please provide a title.')")
        prompt_parts.append("    2) SECOND: After user provides title, ask for priority ONLY (e.g., 'What's the priority? (low/medium/high/urgent)')")
        prompt_parts.append("    3) THIRD: After user provides priority, ask for deadline ONLY (e.g., 'Is there a deadline? (If not, say 'no' or 'none')')")
        prompt_parts.append("    4) FINAL: Execute when title+priority are ready (deadline can be null)")
        prompt_parts.append("  CRITICAL: DO NOT ask for multiple fields at once. Ask ONE field at a time, wait for user response, then ask the next field.")
        prompt_parts.append("  CRITICAL: Check conversation history to see what was already asked. If title was asked but not provided, ask for title again.")
        prompt_parts.append("  CRITICAL: If user provides multiple fields at once (e.g., 'add task buy milk high priority'), extract all fields but still follow the workflow order in your reply.")
        prompt_parts.append("- For 'update_task': Set ready=true ONLY if task is unambiguous AND title AND priority are provided/confirmed AND user explicitly confirmed (said 'yes'/'כן'/'confirm').")
        prompt_parts.append("  REQUIRED FIELDS for update_task:")
        prompt_parts.append("    - ref.task_id OR ref.title (mandatory - must identify which task to update)")
        prompt_parts.append("    - fields.title (mandatory - new title)")
        prompt_parts.append("    - fields.priority (mandatory - new priority)")
        prompt_parts.append("    - fields.deadline (optional - ask but can be null)")
        prompt_parts.append("  WORKFLOW (MUST FOLLOW THIS ORDER - ONE STEP AT A TIME):")
        prompt_parts.append("    1) FIRST: Identify which task to update (ask if unclear)")
        prompt_parts.append("    2) SECOND: Ask for new title (or confirm existing)")
        prompt_parts.append("    3) THIRD: Ask for new priority")
        prompt_parts.append("    4) FOURTH: Ask for deadline (can skip)")
        prompt_parts.append("    5) FIFTH: Ask for confirmation (e.g., 'Are you ready to update? (yes/no)')")
        prompt_parts.append("    6) FINAL: Execute ONLY after explicit confirmation")
        prompt_parts.append("  CRITICAL: DO NOT ask for multiple fields at once. Ask ONE field at a time, wait for user response, then ask the next field.")
        prompt_parts.append("  CRITICAL: If the assistant asked 'Are you ready?' or 'Confirm update?' and user replied 'yes'/'כן'/'confirm', then:")
        prompt_parts.append("    - Set intent='update_task'")
        prompt_parts.append("    - Set ready=true")
        prompt_parts.append("    - Set ref.task_id or ref.title to identify the task")
        prompt_parts.append("    - Set fields.title and fields.priority with the new values")
        prompt_parts.append("- For 'delete_task': Set ready=true ONLY if task is unambiguous AND user explicitly confirmed (said 'yes'/'כן'/'ok'/'אוקיי').")
        prompt_parts.append("  REQUIRED for delete_task:")
        prompt_parts.append("    - ref.task_id OR ref.title (mandatory - must identify which task to delete)")
        prompt_parts.append("    - User explicit confirmation (mandatory - user must say 'yes'/'כן'/'ok'/'אוקיי' after being asked)")
        prompt_parts.append("  WORKFLOW: 1) Identify task → 2) Present task description → 3) Ask for confirmation → 4) Execute ONLY after explicit confirmation")
        prompt_parts.append("  CRITICAL: If the assistant asked 'Are you sure?' or 'בטוח?' and user replied 'yes'/'כן'/'ok'/'אוקיי', then:")
        prompt_parts.append("    - Set intent='delete_task' (NOT 'potential_delete')")
        prompt_parts.append("    - Set ready=true")
        prompt_parts.append("    - Set ref.task_id or ref.title to identify the task")
        prompt_parts.append("  CRITICAL: If user wrote something else (not 'yes'/'כן'/'ok'/'אוקיי'), set ready=false and clear history.")
        prompt_parts.append("- For 'complete_task': Set ready=true ONLY if task is unambiguous. confidence>=0.8 only if task reference is clear.")
        prompt_parts.append("- If information is missing or ambiguous → set ready=false, confidence<0.8, and list missing_fields")
        prompt_parts.append("- Extract fields progressively from the conversation (title, priority, deadline, etc.)")
        prompt_parts.append("- NEVER set ready=true if required fields (title, priority) are missing")
        prompt_parts.append("- ALWAYS ask about deadline as the final step before execution (user can say 'no' or 'skip' to set it as null)")
        prompt_parts.append("")
        prompt_parts.append("CONFIDENCE CALCULATION (CRITICAL - MUST BE A NUMBER 0.0-1.0):")
        prompt_parts.append("- confidence MUST be a number between 0.0 and 1.0 (e.g., 0.8, 0.9, 0.5)")
        prompt_parts.append("- DO NOT use strings like 'A A' or 'high' - ONLY use numbers")
        prompt_parts.append("- High confidence (>=0.8): All required information is clear and unambiguous")
        prompt_parts.append("- Medium confidence (0.5-0.7): Some information is present but incomplete or ambiguous")
        prompt_parts.append("- Low confidence (<0.5): Information is missing or very unclear")
        prompt_parts.append("- Example: If user says 'add task buy milk' → confidence=0.9 (title is clear)")
        prompt_parts.append("- Example: If user says 'add task' → confidence=0.3 (title is missing)")
        prompt_parts.append("- Example: If user says 'medium' after you asked 'what priority?' → confidence=0.8 (answering your question)")
        prompt_parts.append("")
        prompt_parts.append("Generate a helpful, conversational response. Be concise and friendly.")
        prompt_parts.append("Respond naturally as if you're helping the user manage their tasks.")
        prompt_parts.append("")
        prompt_parts.append("=" * 50)
        prompt_parts.append("CRITICAL LANGUAGE INSTRUCTIONS:")
        prompt_parts.append("=" * 50)
        prompt_parts.append("1. The user may write in Hebrew (עברית), English, or mix both languages.")
        prompt_parts.append("2. You MUST respond in the EXACT same language(s) the user used.")
        prompt_parts.append("3. If the user writes in Hebrew → respond in Hebrew.")
        prompt_parts.append("4. If the user writes in English → respond in English.")
        prompt_parts.append("5. Understand Hebrew slang, informal expressions, and common phrases.")
        prompt_parts.append("6. Examples of Hebrew you should understand:")
        prompt_parts.append("   - 'מה המשימות שלי?' = 'What are my tasks?'")
        prompt_parts.append("   - 'תוסיף משימה' = 'Add a task'")
        prompt_parts.append("   - 'מה דחוף לי?' = 'What's urgent for me?'")
        prompt_parts.append("   - 'סמן כבוצע' = 'Mark as done'")
        prompt_parts.append("   - 'תראה לי סיכום שבועי' = 'Show me weekly summary'")
        prompt_parts.append("7. DO NOT translate Hebrew to English in your response.")
        prompt_parts.append("8. DO NOT respond in English if the user wrote in Hebrew.")
        prompt_parts.append("=" * 50)
        
        return "\n".join(prompt_parts)





async def _generate_llm_response(self, request: ChatRequest) -> Optional[ChatResponse]:
        """
        Generate response using LLM (OpenAI).
        
        Args:
            request: Chat request with message and context data
        
        Returns:
            ChatResponse if successful, None if failed
        """
        if not self._openai_client:
            return None
        
        try:
            # Build prompt
            prompt = self._build_prompt(request)
            
            logger.debug(f"Sending request to OpenAI (model: {settings.MODEL_NAME})")
            
            # Call OpenAI API
            response = await self._openai_client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for TaskGenius, a task management system. Provide concise, friendly responses.\n\nYOUR CORE RESPONSIBILITIES:\n1. Understand user intent (create/update/delete/list/insights)\n2. Ask for clarification when information is missing or ambiguous\n3. Refer to specific tasks when relevant (use task titles, deadlines, priorities)\n4. Be aware of task context (deadlines, priorities, statuses)\n5. NEVER assume or guess - always ask if unclear\n\nCRITICAL LANGUAGE RULES:\n- You MUST support Hebrew (עברית) and English\n- If the user writes in Hebrew, you MUST respond in Hebrew\n- If the user writes in English, respond in English\n- If the user mixes languages, respond in the same mix\n- Understand Hebrew slang, informal expressions, and common phrases\n- Examples of Hebrew task management phrases:\n  * 'מה המשימות שלי?' = 'What are my tasks?'\n  * 'תוסיף משימה' = 'Add a task'\n  * 'מה דחוף לי?' = 'What's urgent for me?'\n  * 'סמן כבוצע' = 'Mark as done'\n- Always match the user's language preference"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300,
                timeout=settings.LLM_TIMEOUT,
            )
            
            # Extract reply and command from response
            content = response.choices[0].message.content.strip()
            
            if not content:
                logger.warning("Empty reply from LLM")
                return None
            
            # Parse structured output (Phase 3)
            reply, command = self._parse_llm_response(content, request)
            
            if not reply:
                logger.warning("Could not extract reply from LLM response")
                return None
            
            # Determine intent from original message (more reliable than extracting from reply)
            # Use the original message to detect intent, as it's more accurate
            intent = self._extract_intent_from_message(request.message, request)
            
            # Generate suggestions based on intent
            suggestions = self._generate_suggestions(intent, request)
            
            return ChatResponse(
                reply=reply,
                intent=intent,
                suggestions=suggestions,
                command=command
            )
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return None
        




def _parse_llm_response(self, content: str, request: ChatRequest) -> tuple[str, Optional[Command]]:
        """
        Parse LLM response to extract reply and command (Phase 3).
        
        Expected format:
        REPLY: [natural text]
        COMMAND: [JSON object]
        
        Returns:
            (reply, command) tuple
        """
        reply = ""
        command = None
        
        # Try to parse structured format
        reply_match = re.search(r'REPLY:\s*(.+?)(?=COMMAND:|$)', content, re.DOTALL | re.IGNORECASE)
        command_match = re.search(r'COMMAND:\s*(\{.*\})', content, re.DOTALL | re.IGNORECASE)
        
        if reply_match:
            reply = reply_match.group(1).strip()
            # Clean up: Remove any JSON objects that might have leaked into the reply
            # This handles cases where LLM includes JSON in the REPLY section
            json_pattern = r'\{[^{}]*"intent"[^{}]*\}'
            reply = re.sub(json_pattern, '', reply, flags=re.DOTALL)
            # Remove any remaining JSON-like structures
            reply = re.sub(r'\{[^{}]*\}', '', reply, flags=re.DOTALL)
            # Clean up extra whitespace
            reply = re.sub(r'\s+', ' ', reply).strip()
        else:
            # Fallback: use entire content as reply, but clean it first
            reply = content
            # Try to remove COMMAND section if it exists
            reply = re.sub(r'COMMAND:\s*\{.*\}', '', reply, flags=re.DOTALL | re.IGNORECASE)
            # Remove any JSON objects
            reply = re.sub(r'\{[^{}]*"intent"[^{}]*\}', '', reply, flags=re.DOTALL)
            reply = re.sub(r'\{[^{}]*\}', '', reply, flags=re.DOTALL)
            reply = re.sub(r'\s+', ' ', reply).strip()
        
        if command_match:
            try:
                command_json = command_match.group(1).strip()
                command_dict = json.loads(command_json)
                
                # Validate and parse confidence (must be a number between 0.0 and 1.0)
                confidence_raw = command_dict.get("confidence", 0.0)
                try:
                    confidence = float(confidence_raw)
                    # Clamp to valid range
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid confidence value: {confidence_raw}, defaulting to 0.0")
                    confidence = 0.0
                
                # Validate required fields for add_task and update_task
                intent = command_dict.get("intent", "clarify")
                fields = command_dict.get("fields", {})
                ready = command_dict.get("ready", False)
                missing_fields = command_dict.get("missing_fields", [])
                
                # Enforce required fields: title and priority for add_task/update_task
                # CRITICAL: Check conversation history to determine which field should be asked next
                if intent in ["add_task", "update_task"]:
                    # Check conversation history to see what was already asked/collected
                    last_assistant_msg = None
                    if request.conversation_history:
                        for msg in reversed(request.conversation_history[-5:]):
                            if msg.get("role") == "assistant":
                                last_assistant_msg = msg.get("content", "").lower()
                                break
                    
                    # For add_task: Check if fields were collected in order
                    if intent == "add_task":
                        # Check if title is missing
                        if not fields.get("title"):
                            ready = False
                            if "title" not in missing_fields:
                                missing_fields.append("title")
                            # If last assistant message didn't ask for title, it should be asked first
                            if last_assistant_msg and "title" not in last_assistant_msg and "כותרת" not in last_assistant_msg:
                                # Title should be asked first - clear priority if it was set
                                if fields.get("priority"):
                                    fields["priority"] = None
                                    if "priority" in missing_fields:
                                        missing_fields.remove("priority")
                        # Check if priority is missing (only if title is present)
                        elif not fields.get("priority"):
                            ready = False
                            if "priority" not in missing_fields:
                                missing_fields.append("priority")
                            # If last assistant message didn't ask for priority, it should be asked second
                            if last_assistant_msg and "priority" not in last_assistant_msg and "עדיפות" not in last_assistant_msg:
                                # Priority should be asked second - clear deadline if it was set
                                if fields.get("deadline"):
                                    fields["deadline"] = None
                                    if "deadline" in missing_fields:
                                        missing_fields.remove("deadline")
                    
                    # For update_task: Similar logic but with confirmation step
                    elif intent == "update_task":
                        if not fields.get("title"):
                            ready = False
                            if "title" not in missing_fields:
                                missing_fields.append("title")
                        if not fields.get("priority"):
                            ready = False
                            if "priority" not in missing_fields:
                                missing_fields.append("priority")
                    
                    # Rule 8: For update_task, check for explicit confirmation
                    # CRITICAL: Similar to add_task deadline logic - if user didn't write "yes"/"ok"/"כן"/"אוקיי", 
                    # don't execute and clear history (so next commands rely on DB)
                    if intent == "update_task":
                        has_confirmation = False
                        if request.conversation_history:
                            # Check last assistant message for confirmation request
                            last_assistant_msg = None
                            for msg in reversed(request.conversation_history[-5:]):
                                if msg.get("role") == "assistant":
                                    last_assistant_msg = msg.get("content", "").lower()
                                    break
                            
                            if last_assistant_msg and ("confirm" in last_assistant_msg or "ready" in last_assistant_msg or "אישור" in last_assistant_msg or "מוכן" in last_assistant_msg or "בטוח" in last_assistant_msg):
                                # Check if user confirmed in current message
                                message_lower = request.message.lower().strip()
                                confirm_keywords = ["yes", "כן", "confirm", "אשר", "ok", "אוקיי", "ready", "מוכן", "okay"]
                                # CRITICAL: Only accept exact confirmation keywords, not partial matches
                                # This prevents false positives (e.g., "ok" in "look" or "כן" in "כןן")
                                message_words = message_lower.split()
                                has_confirmation = any(keyword in message_words for keyword in confirm_keywords) or message_lower in confirm_keywords
                                
                                if has_confirmation:
                                    # User confirmed - set ready=true if all other fields are present
                                    logger.debug("Update task: User confirmed, setting ready=true if fields are present")
                                    # If title and priority are present, force ready=true
                                    if fields.get("title") and fields.get("priority"):
                                        ready = True
                                        intent = "update_task"
                                        # Remove confirmation from missing_fields if it was there
                                        if "confirmation" in missing_fields:
                                            missing_fields.remove("confirmation")
                                else:
                                    # User wrote something else (not "yes"/"ok"/"כן"/"אוקיי")
                                    # Don't execute, but mark as needing history clear (will be handled by frontend)
                                    logger.debug(f"Update task: User wrote '{request.message}' instead of confirmation. Not executing.")
                                    ready = False
                                    # Set intent to indicate this was a non-confirmation response
                                    # Frontend will clear history based on this
                                    if "confirmation" not in missing_fields:
                                        missing_fields.append("confirmation")
                        
                        if not has_confirmation:
                            # No confirmation yet - set ready=false
                            ready = False
                            if "confirmation" not in missing_fields:
                                missing_fields.append("confirmation")
                    
                    # Rule 9: For delete_task, check for explicit confirmation (similar logic)
                    if intent == "delete_task":
                        has_confirmation = False
                        if request.conversation_history:
                            # Check last assistant message for confirmation request
                            last_assistant_msg = None
                            for msg in reversed(request.conversation_history[-5:]):
                                if msg.get("role") == "assistant":
                                    last_assistant_msg = msg.get("content", "").lower()
                                    break
                            
                            if last_assistant_msg and ("confirm" in last_assistant_msg or "בטוח" in last_assistant_msg or "sure" in last_assistant_msg or "אישור" in last_assistant_msg):
                                # Check if user confirmed in current message
                                message_lower = request.message.lower().strip()
                                confirm_keywords = ["yes", "כן", "confirm", "אשר", "ok", "אוקיי", "okay"]
                                # CRITICAL: Only accept exact confirmation keywords
                                message_words = message_lower.split()
                                has_confirmation = any(keyword in message_words for keyword in confirm_keywords) or message_lower in confirm_keywords
                                
                                if has_confirmation:
                                    # User confirmed - set ready=true
                                    logger.debug("Delete task: User confirmed, setting ready=true")
                                    ready = True
                                    # Force intent to be delete_task (not potential_delete)
                                    if intent == "potential_delete":
                                        intent = "delete_task"
                                    # Remove confirmation from missing_fields if it was there
                                    if "confirmation" in missing_fields:
                                        missing_fields.remove("confirmation")
                                else:
                                    # User wrote something else (not "yes"/"ok"/"כן"/"אוקיי")
                                    # Don't execute, but mark as needing history clear
                                    logger.debug(f"Delete task: User wrote '{request.message}' instead of confirmation. Not executing.")
                                    ready = False
                                    if "confirmation" not in missing_fields:
                                        missing_fields.append("confirmation")
                        
                        if not has_confirmation:
                            # No confirmation yet - set ready=false
                            ready = False
                            if "confirmation" not in missing_fields:
                                missing_fields.append("confirmation")
                    
                    # Rule 2: Deadline must be asked as LAST step (only for add_task, or update_task if confirmation already received)
                    # CRITICAL: Only check deadline if priority is already present (for add_task)
                    # Order must be: title → priority → deadline
                    if intent == "add_task":
                        # Only check deadline if priority is already present
                        if fields.get("priority"):
                            deadline = fields.get("deadline")
                            if deadline is not None and deadline != "":
                                # Rule 3: Validate deadline format and clarity
                                is_valid, normalized = self._validate_deadline_format(deadline)
                                is_ambiguous = self._is_deadline_ambiguous(deadline, request.conversation_history)
                                
                                # CRITICAL: Check if user explicitly said "no" or "none" (case-insensitive)
                                deadline_lower = str(deadline).lower().strip()
                                none_keywords = ["none", "no", "אין", "לא", "null", "skip"]
                                is_explicit_none = deadline_lower in none_keywords
                                
                                if is_explicit_none:
                                    # User explicitly said "no" or "none" - set to None
                                    fields["deadline"] = None
                                    # Don't set ready=false for this - deadline is optional
                                elif not is_valid or is_ambiguous:
                                    # Deadline is unclear or invalid (including old dates like 2023)
                                    # Set ready=false and ask for numeric format
                                    ready = False
                                    if "deadline" not in missing_fields:
                                        missing_fields.append("deadline")
                                    # Update fields to None to indicate it needs clarification
                                    fields["deadline"] = None
                                    logger.warning(f"Invalid or ambiguous deadline: {deadline}. Will ask for numeric format.")
                                    # Note: The reply will be generated by LLM based on the prompt instructions
                                    # The prompt explicitly tells LLM to ask for numeric format if date is unclear
                                    # The LLM should respond with: "אנא תן תאריך במספרים (למשל: 2024-01-20), או כתוב 'לא' אם אין תאריך יעד"
                                else:
                                    # Valid and clear - normalize it
                                    fields["deadline"] = normalized
                            else:
                                # Rule 2: Check if deadline was asked as last step (only if priority is present)
                                if not self._was_deadline_asked_last(request.conversation_history):
                                    # Deadline wasn't asked yet - must be asked before ready
                                    ready = False
                                    if "deadline" not in missing_fields:
                                        missing_fields.append("deadline")
                        # If priority is not present, don't check deadline yet (priority must come first)
                        else:
                            # Priority is missing - deadline should not be checked yet
                            if "deadline" in missing_fields:
                                missing_fields.remove("deadline")
                            if fields.get("deadline"):
                                # Clear deadline if it was set before priority
                                fields["deadline"] = None
                    elif intent == "update_task":
                        # For update_task, deadline is optional - only check if confirmation was already received
                        # (deadline check happens before confirmation in the flow)
                        deadline = fields.get("deadline")
                        if deadline is not None and deadline != "":
                            # Rule 3: Validate deadline format and clarity
                            is_valid, normalized = self._validate_deadline_format(deadline)
                            is_ambiguous = self._is_deadline_ambiguous(deadline, request.conversation_history)
                            
                            # CRITICAL: Check if user explicitly said "no" or "none" (case-insensitive)
                            deadline_lower = str(deadline).lower().strip()
                            none_keywords = ["none", "no", "אין", "לא", "null", "skip"]
                            is_explicit_none = deadline_lower in none_keywords
                            
                            if is_explicit_none:
                                # User explicitly said "no" or "none" - set to None
                                fields["deadline"] = None
                                # Don't set ready=false for this - deadline is optional
                            elif not is_valid or is_ambiguous:
                                # Deadline is unclear or invalid (including old dates like 2023)
                                # Set ready=false and ask for numeric format
                                ready = False
                                if "deadline" not in missing_fields:
                                    missing_fields.append("deadline")
                                # Update fields to None to indicate it needs clarification
                                fields["deadline"] = None
                                logger.warning(f"Invalid or ambiguous deadline: {deadline}. Will ask for numeric format.")
                            else:
                                # Valid and clear - normalize it
                                fields["deadline"] = normalized
                
                # For update_task, ensure ref is set (extract from conversation if missing)
                ref = command_dict.get("ref")
                if intent == "update_task" and not ref:
                    # Try to extract task reference from conversation history
                    if request.conversation_history and request.tasks:
                        # Look for task title in recent messages
                        for msg in reversed(request.conversation_history[-10:]):
                            content = msg.get("content", "")
                            for task in request.tasks:
                                task_title = task.get("title", "")
                                if task_title and task_title.lower() in content.lower():
                                    ref = {"task_id": task.get("id"), "title": task_title}
                                    logger.debug(f"Extracted task ref from conversation: {ref}")
                                    break
                            if ref:
                                break
                
                # Create Command object
                command = Command(
                    intent=intent,
                    confidence=confidence,
                    fields=fields,
                    ref=ref,
                    filter=command_dict.get("filter"),
                    ready=ready,
                    missing_fields=missing_fields if missing_fields else None
                )
                logger.debug(f"Parsed command: intent={command.intent}, confidence={command.confidence}, ready={command.ready}, missing_fields={command.missing_fields}")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse command JSON: {e}")
                # Continue without command - backward compatible
        
        return reply, command







def _extract_intent_from_message(self, message: str, request: ChatRequest) -> Optional[str]:
        """
        Extract intent from user message (more reliable than extracting from LLM reply).
        Phase 2: Improved intent detection with potential_* intents.
        """
        message_lower = message.lower()
        
        # Check for phrases first (more specific), then single words
        # Hebrew phrases for create
        create_phrases_hebrew = ["רוצה להוסיף", "רוצה ליצור", "אני רוצה להוסיף", "אני רוצה ליצור", "בוא נוסיף", "בוא ניצור"]
        # Hebrew phrases for update
        update_phrases_hebrew = ["רוצה לעדכן", "רוצה לשנות", "אני רוצה לעדכן", "אני רוצה לשנות", "בוא נעדכן", "בוא נשנה"]
        # Hebrew phrases for delete
        delete_phrases_hebrew = ["רוצה למחוק", "רוצה להסיר", "אני רוצה למחוק", "אני רוצה להסיר", "בוא נמחק", "בוא נסיר"]
        
        # Check for task insights (deadlines, priorities, urgency) - highest priority
        if any(word in message_lower for word in ["summary", "insights", "report", "weekly", "סיכום", "דוח"]):
            return "get_insights"
        elif any(word in message_lower for word in ["urgent", "priority", "deadline", "due", "דחוף", "עדיפות", "תאריך"]):
            return "task_insights"
        
        # Check for create/update/delete intents FIRST (before list_tasks)
        # These are action verbs - more specific than "list" or "show"
        # Check phrases first (more specific), then single words
        
        # CREATE - check phrases first
        if any(phrase in message_lower for phrase in create_phrases_hebrew):
            return "potential_create"
        # CREATE - check single words
        elif any(word in message_lower for word in ["create", "add", "new", "צור", "הוסף", "תוסיף"]):
            return "potential_create"
        
        # DELETE - check phrases first (BEFORE update - more destructive, needs higher priority)
        if any(phrase in message_lower for phrase in delete_phrases_hebrew):
            return "potential_delete"
        # DELETE - check single words (BEFORE update)
        elif any(word in message_lower for word in ["delete", "remove", "מחק", "הסר", "תמחק", "תמחקי"]):
            return "potential_delete"
        
        # UPDATE - check phrases first
        elif any(phrase in message_lower for phrase in update_phrases_hebrew):
            return "update_task"
        # UPDATE - check single words
        elif any(word in message_lower for word in ["update", "change", "modify", "edit", "עדכן", "שנה", "ערוך"]):
            return "update_task"
        elif any(word in message_lower for word in ["complete", "done", "finish", "בוצע", "סיים", "סיימתי"]):
            return "update_task"
        
        # Check for list tasks (after action verbs)
        # Only match if it's clearly a list query, not an action
        # Exclude "מה" if there are action verbs (create/update/delete)
        action_verbs = ["create", "add", "update", "delete", "remove", "צור", "הוסף", "עדכן", "מחק", "להוסיף", "ליצור", "לעדכן", "למחוק", "להסיר"]
        has_action_verb = any(verb in message_lower for verb in action_verbs)
        
        if any(word in message_lower for word in ["list", "show", "tasks", "רשימה", "הצג"]):
            # Clear list commands
            return "list_tasks"
        elif "מה" in message_lower and not has_action_verb:
            # "מה" only if no action verbs (e.g., "מה המשימות שלי?" not "מה המשימה שתרצה להוסיף?")
            return "list_tasks"
        elif "what" in message_lower and not has_action_verb:
            # "what" only if no action verbs
            return "list_tasks"
        
        return "unknown"

def _generate_suggestions(self, intent: Optional[str], request: ChatRequest) -> List[str]:
        """Generate suggestions based on intent."""
        if intent == "list_tasks":
            return ["View all tasks", "Filter by status", "Create new task"]
        elif intent == "get_insights" or intent == "task_insights":
            return ["View detailed summary", "Filter by category", "View urgent tasks"]
        elif intent == "create_task" or intent == "potential_create":
            return ["Set deadline", "Add category", "Set priority"]
        elif intent == "update_task":
            return ["Change priority", "Change deadline", "Change status"]
        elif intent == "potential_delete":
            return ["Confirm deletion", "Cancel", "View all tasks"]
        else:
            return ["List tasks", "Create task", "Get help"]
