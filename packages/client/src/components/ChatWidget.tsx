/**
 * ChatWidget
 * 
 * Purpose: Floating chat interface for conversational task management
 * 
 * Responsibilities:
 * - Display collapsible chat panel
 * - Show chat message history
 * - Accept user input and send to core-api (via chatApi)
 * - Display AI responses with action results
 * - Notify parent when tasks are created via chat
 * 
 * API: chatApi.sendMessage(), chatApi.getHistory()
 * 
 * ARCHITECTURE NOTE:
 * - Messages go to core-api, which orchestrates with chatbot-service internally
 * - Client NEVER communicates directly with chatbot-service
 * - core-api executes any task mutations and returns results
 */

import { useState, useRef, useEffect, type FormEvent } from 'react';
import { chatApi } from '@/api';
import type { Task, ChatMessage } from '@/types';

interface ChatWidgetProps {
    onTaskCreated?: (task: Task) => void;
}

export function ChatWidget({ onTaskCreated }: ChatWidgetProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Load chat history on mount
    useEffect(() => {
        if (isOpen && messages.length === 0) {
            loadHistory();
        }
    }, [isOpen]);

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const loadHistory = async () => {
        try {
            const history = await chatApi.getHistory(50);
            setMessages(history.messages);
        } catch (err) {
            console.error('Failed to load chat history:', err);
        }
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage: ChatMessage = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content: input,
            timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await chatApi.sendMessage({ message: input });
            setMessages((prev) => [...prev, response.message]);

            // If tasks were created, notify parent
            // (In a real implementation, you'd fetch the created tasks)
            // if (response.affectedTasks?.length && onTaskCreated) { ... }
        } catch (err) {
            const errorMessage: ChatMessage = {
                id: `error-${Date.now()}`,
                role: 'assistant',
                content: 'Sorry, something went wrong. Please try again.',
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`chat-widget ${isOpen ? 'open' : ''}`}>
            <button
                className="chat-toggle"
                onClick={() => setIsOpen(!isOpen)}
                aria-label={isOpen ? 'Close chat' : 'Open chat'}
            >
                {isOpen ? '×' : '💬'}
            </button>

            {isOpen && (
                <div className="chat-panel">
                    <div className="chat-header">
                        <h3>Chat Assistant</h3>
                        <p>Ask me to create tasks, show status, and more</p>
                    </div>

                    <div className="chat-messages">
                        {messages.length === 0 && (
                            <div className="chat-empty">
                                <p>Try: "Add a task to review the project proposal"</p>
                            </div>
                        )}
                        {messages.map((msg) => (
                            <div key={msg.id} className={`chat-message ${msg.role}`}>
                                <div className="message-content">{msg.content}</div>
                                {msg.actions && msg.actions.length > 0 && (
                                    <div className="message-actions">
                                        {msg.actions.map((action, i) => (
                                            <span key={i} className="action-badge">
                                                ✓ {action.summary}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                        {loading && (
                            <div className="chat-message assistant loading">
                                <span>Thinking...</span>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <form className="chat-input" onSubmit={handleSubmit}>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Type a message..."
                            disabled={loading}
                        />
                        <button type="submit" disabled={loading || !input.trim()}>
                            Send
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}
