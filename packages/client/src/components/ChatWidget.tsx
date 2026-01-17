/**
 * ChatWidget
 * 
 * Purpose: Floating chat interface for conversational task management
 * 
 * Responsibilities:
 * - Display collapsible chat panel
 * - Show chat message history (last N messages)
 * - Accept user input and send to core-api (via chatApi)
 * - Display AI responses with suggestions
 * - Maintain conversation history in memory
 * 
 * API: chatApi.sendMessage()
 * 
 * ARCHITECTURE NOTE:
 * - Messages go to core-api, which orchestrates with chatbot-service internally
 * - Client NEVER communicates directly with chatbot-service
 * - core-api executes any task mutations and returns results
 */

import { useState, useRef, useEffect, type FormEvent } from 'react';
import { chatApi } from '@/api';
import type { Task } from '@/types';

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    intent?: string;
    suggestions?: string[];
}

interface ChatWidgetProps {
    onTaskCreated?: (task: Task) => void;
}

const CHAT_HISTORY_KEY = 'taskgenius_chat_history';
const CHAT_HISTORY_EXPIRY_DAYS = 7; // Keep history for 7 days

interface StoredChatHistory {
    messages: ChatMessage[];
    timestamp: number;
}

export function ChatWidget({ onTaskCreated }: ChatWidgetProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Load chat history from localStorage on mount
    useEffect(() => {
        const loadHistory = () => {
            try {
                const stored = localStorage.getItem(CHAT_HISTORY_KEY);
                if (stored) {
                    const history: StoredChatHistory = JSON.parse(stored);
                    const now = Date.now();
                    const expiryTime = CHAT_HISTORY_EXPIRY_DAYS * 24 * 60 * 60 * 1000;
                    
                    // Check if history is still valid (not expired)
                    if (now - history.timestamp < expiryTime) {
                        // Convert timestamp strings back to Date objects
                        const loadedMessages = history.messages.map(msg => ({
                            ...msg,
                            timestamp: new Date(msg.timestamp)
                        }));
                        setMessages(loadedMessages);
                    } else {
                        // History expired, clear it
                        localStorage.removeItem(CHAT_HISTORY_KEY);
                    }
                }
            } catch (err) {
                console.error('Failed to load chat history:', err);
                localStorage.removeItem(CHAT_HISTORY_KEY);
            }
        };
        
        loadHistory();
    }, []);

    // Save chat history to localStorage whenever messages change
    useEffect(() => {
        if (messages.length > 0) {
            try {
                const history: StoredChatHistory = {
                    messages: messages.map(msg => ({
                        ...msg,
                        timestamp: msg.timestamp.toISOString() // Convert Date to string for storage
                    })),
                    timestamp: Date.now()
                };
                localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(history));
            } catch (err) {
                console.error('Failed to save chat history:', err);
            }
        }
    }, [messages]);


    // Scroll to bottom when new messages arrive
    useEffect(() => {
        if (isOpen) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isOpen]);

    // Focus input when chat opens
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage: ChatMessage = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: input.trim(),
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        const currentInput = input.trim();
        setInput('');
        setLoading(true);

        try {
            const response = await chatApi.sendMessage({ message: currentInput });
            
            const assistantMessage: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: response.reply,
                timestamp: new Date(),
                intent: response.intent,
                suggestions: response.suggestions,
            };

            setMessages((prev) => [...prev, assistantMessage]);

            // Keep only last 50 messages in memory
            setMessages((prev) => prev.slice(-50));
        } catch (err) {
            const errorMessage: ChatMessage = {
                id: `error-${Date.now()}`,
                role: 'assistant',
                content: 'Sorry, something went wrong. Please try again.',
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
            // Refocus input after response
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const formatTime = (date: Date): string => {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
    };

    return (
        <div className={`chat-widget ${isOpen ? 'open' : ''}`}>
            <button
                className="chat-toggle"
                onClick={() => setIsOpen(!isOpen)}
                aria-label={isOpen ? 'Close chat' : 'Open chat'}
                title={isOpen ? 'Close chat' : 'Open chat'}
            >
                {isOpen ? '×' : '💬'}
                {!isOpen && messages.length > 0 && (
                    <span className="chat-badge">{messages.length}</span>
                )}
            </button>

            {isOpen && (
                <div className="chat-panel">
                    <div className="chat-header">
                        <div>
                            <h3>TaskGenius Assistant</h3>
                            <p>Ask me about your tasks, create new ones, or get insights</p>
                        </div>
                        {messages.length > 0 && (
                            <button
                                className="chat-clear"
                                onClick={() => {
                                    setMessages([]);
                                    localStorage.removeItem(CHAT_HISTORY_KEY);
                                }}
                                title="Clear conversation"
                            >
                                Clear
                            </button>
                        )}
                    </div>

                    <div className="chat-messages">
                        {messages.length === 0 && (
                            <div className="chat-empty">
                                <div className="chat-empty-icon">💬</div>
                                <p>Start a conversation!</p>
                                <div className="chat-examples">
                                    <p>Try asking:</p>
                                    <ul>
                                        <li>"What are my tasks?"</li>
                                        <li>"Show me my weekly summary"</li>
                                        <li>"What's urgent for me?"</li>
                                        <li>"Add a task to review the project proposal"</li>
                                    </ul>
                                </div>
                            </div>
                        )}
                        {messages.map((msg) => (
                            <div key={msg.id} className={`chat-message ${msg.role}`}>
                                <div className="message-avatar">
                                    {msg.role === 'user' ? '👤' : '🤖'}
                                </div>
                                <div className="message-bubble">
                                    <div className="message-content">{msg.content}</div>
                                    {msg.suggestions && msg.suggestions.length > 0 && (
                                        <div className="message-suggestions">
                                            {msg.suggestions.map((suggestion, i) => (
                                                <button
                                                    key={i}
                                                    className="suggestion-chip"
                                                    onClick={() => setInput(suggestion)}
                                                >
                                                    {suggestion}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                    <div className="message-time">{formatTime(msg.timestamp)}</div>
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="chat-message assistant loading">
                                <div className="message-avatar">🤖</div>
                                <div className="message-bubble">
                                    <div className="typing-indicator">
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <form className="chat-input" onSubmit={handleSubmit}>
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Type a message..."
                            disabled={loading}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            }}
                        />
                        <button 
                            type="submit" 
                            disabled={loading || !input.trim()}
                            title="Send message (Enter)"
                        >
                            {loading ? '⏳' : '➤'}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}
