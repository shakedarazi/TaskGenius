/**
 * ChatWidget - Minimal suggestion-based chat UI
 */

import { useState, useRef, useEffect, type FormEvent } from 'react';
import { chatApi } from '@/api';
import type { TaskSuggestion } from '@/types';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

export function ChatWidget() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [suggestions, setSuggestions] = useState<TaskSuggestion[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Scroll to bottom when messages change
    useEffect(() => {
        if (isOpen) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isOpen]);

    // Focus input when chat opens
    useEffect(() => {
        if (isOpen) inputRef.current?.focus();
    }, [isOpen]);

    // Format suggestion for display
    const formatSuggestion = (s: TaskSuggestion, index: number): string => {
        const priority = s.priority === 'high' || s.priority === 'urgent' ? ' ⚡' : '';
        return `${index + 1}. ${s.title}${priority}`;
    };

    // Handle message submit
    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        const text = input.trim();
        if (!text || loading) return;

        // Check if input is a number (selection)
        const num = parseInt(text, 10);
        if (!isNaN(num) && num >= 1 && num <= suggestions.length) {
            await handleSelection(num);
            return;
        }

        // Regular message
        const userMsg: Message = {
            id: `u-${Date.now()}`,
            role: 'user',
            content: text,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setSuggestions([]);
        setLoading(true);

        try {
            const response = await chatApi.sendMessage(text);
            
            const assistantMsg: Message = {
                id: `a-${Date.now()}`,
                role: 'assistant',
                content: response.reply,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, assistantMsg]);
            setSuggestions(response.suggestions || []);
        } catch {
            setMessages(prev => [...prev, {
                id: `e-${Date.now()}`,
                role: 'assistant',
                content: 'Sorry, something went wrong. Please try again.',
                timestamp: new Date(),
            }]);
        } finally {
            setLoading(false);
            setTimeout(() => inputRef.current?.focus(), 50);
        }
    };

    // Handle suggestion selection (click or number input)
    const handleSelection = async (num: number) => {
        setInput('');
        setLoading(true);

        try {
            const response = await chatApi.selectSuggestion(num);
            
            // Clear suggestions after successful add
            setSuggestions([]);
            
            const msg: Message = {
                id: `a-${Date.now()}`,
                role: 'assistant',
                content: response.reply,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, msg]);

            // Notify app that a task was created
            if (response.added_task) {
                window.dispatchEvent(new CustomEvent('taskMutated', { detail: { intent: 'add_task' } }));
            }
        } catch {
            setMessages(prev => [...prev, {
                id: `e-${Date.now()}`,
                role: 'assistant',
                content: 'Failed to add task. Please try again.',
                timestamp: new Date(),
            }]);
        } finally {
            setLoading(false);
            setTimeout(() => inputRef.current?.focus(), 50);
        }
    };

    const formatTime = (d: Date) => d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

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
                        <div>
                            <h3>TaskGenius Assistant</h3>
                            <p>Tell me what you need to do</p>
                        </div>
                        {messages.length > 0 && (
                            <button
                                className="chat-clear"
                                onClick={() => { setMessages([]); setSuggestions([]); }}
                                title="Clear"
                            >
                                Clear
                            </button>
                        )}
                    </div>

                    <div className="chat-messages">
                        {messages.length === 0 && suggestions.length === 0 && (
                            <div className="chat-empty">
                                <div className="chat-empty-icon">💬</div>
                                <p>Start a conversation!</p>
                                <div className="chat-examples">
                                    <p>Try:</p>
                                    <ul>
                                        <li>"I need to prepare for tomorrow's meeting"</li>
                                        <li>"Help me organize my work tasks"</li>
                                    </ul>
                                </div>
                            </div>
                        )}

                        {messages.map(msg => (
                            <div key={msg.id} className={`chat-message ${msg.role}`}>
                                <div className="message-avatar">{msg.role === 'user' ? '👤' : '🤖'}</div>
                                <div className="message-bubble">
                                    <div className="message-content">{msg.content}</div>
                                    <div className="message-time">{formatTime(msg.timestamp)}</div>
                                </div>
                            </div>
                        ))}

                        {/* Suggestions displayed separately */}
                        {suggestions.length > 0 && (
                            <div className="chat-suggestions">
                                <div className="suggestions-header">Click to add or type a number:</div>
                                <ul className="suggestions-list">
                                    {suggestions.map((s, i) => (
                                        <li key={i}>
                                            <button
                                                className="suggestion-item"
                                                onClick={() => handleSelection(i + 1)}
                                                disabled={loading}
                                            >
                                                {formatSuggestion(s, i)}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {loading && (
                            <div className="chat-message assistant loading">
                                <div className="message-avatar">🤖</div>
                                <div className="message-bubble">
                                    <div className="typing-indicator">
                                        <span></span><span></span><span></span>
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
                            onChange={e => setInput(e.target.value)}
                            placeholder={suggestions.length > 0 ? "Type 1-" + suggestions.length + " to add..." : "Type a message..."}
                            disabled={loading}
                        />
                        <button type="submit" disabled={loading || !input.trim()}>
                            {loading ? '⏳' : '➤'}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}
