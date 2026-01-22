/**
 * ChatWidget - Minimal suggestion-based chat UI
 */

import { useState, useRef, useEffect, type FormEvent } from 'react';
import { chatApi, tasksApi } from '@/api';
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
    // Multi-selection state
    const [selected, setSelected] = useState<Set<number>>(new Set());
    const [deadlines, setDeadlines] = useState<Record<number, string>>({});
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

    // Clear selection when suggestions change
    useEffect(() => {
        setSelected(new Set());
        setDeadlines({});
    }, [suggestions]);

    // Toggle selection
    const toggleSelect = (index: number) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(index)) {
                next.delete(index);
            } else {
                next.add(index);
            }
            return next;
        });
    };

    // Set deadline for a suggestion
    const setDeadline = (index: number, value: string) => {
        setDeadlines(prev => ({ ...prev, [index]: value }));
    };

    // Format suggestion for display
    const formatSuggestion = (s: TaskSuggestion): string => {
        const priority = s.priority === 'high' || s.priority === 'urgent' ? ' ⚡' : '';
        return `${s.title}${priority}`;
    };

    // Handle message submit
    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        const text = input.trim();
        if (!text || loading) return;

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

    // Handle adding selected suggestions - direct task creation in parallel
    const handleAddSelected = async () => {
        if (selected.size === 0 || loading) return;
        setLoading(true);

        const indices = Array.from(selected).sort((a, b) => a - b);
        
        try {
            // Build task payloads from selected suggestions
            const createPromises = indices.map(index => {
                const s = suggestions[index];
                const deadline = deadlines[index];
                return tasksApi.createTask({
                    title: s.title,
                    priority: s.priority as 'low' | 'medium' | 'high' | 'urgent',
                    ...(deadline ? { deadline } : {}),
                });
            });

            // Execute all in parallel
            const results = await Promise.all(createPromises);
            const added = results.map(t => t.title);

            // Clear suggestions after successful add
            setSuggestions([]);
            
            const msg: Message = {
                id: `a-${Date.now()}`,
                role: 'assistant',
                content: `✅ Added ${added.length} task${added.length > 1 ? 's' : ''}: ${added.join(', ')}`,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, msg]);

            // Notify app that tasks were created
            window.dispatchEvent(new CustomEvent('taskMutated', { detail: { intent: 'add_task' } }));
        } catch {
            setMessages(prev => [...prev, {
                id: `e-${Date.now()}`,
                role: 'assistant',
                content: 'Failed to add tasks. Please try again.',
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
                            <p>Tell me about your assignments or projects</p>
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
                                <div className="chat-empty-icon">📚</div>
                                <p>Start a conversation!</p>
                                <div className="chat-examples">
                                    <p>Try:</p>
                                    <ul>
                                        <li>"I need to prepare for my final exam"</li>
                                        <li>"Help me organize my course assignments"</li>
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

                        {/* Suggestions with multi-select and deadline */}
                        {suggestions.length > 0 && (
                            <div className="chat-suggestions">
                                <div className="suggestions-header">Select tasks to add:</div>
                                <ul className="suggestions-list">
                                    {suggestions.map((s, i) => (
                                        <li key={i} className="suggestion-row">
                                            <label className="suggestion-checkbox">
                                                <input
                                                    type="checkbox"
                                                    checked={selected.has(i)}
                                                    onChange={() => toggleSelect(i)}
                                                    disabled={loading}
                                                />
                                                <span className="suggestion-label">{i + 1}. {formatSuggestion(s)}</span>
                                            </label>
                                            <input
                                                type="date"
                                                className="suggestion-date"
                                                value={deadlines[i] || ''}
                                                onChange={e => setDeadline(i, e.target.value)}
                                                disabled={loading}
                                                title="Set deadline (optional)"
                                            />
                                        </li>
                                    ))}
                                </ul>
                                <button
                                    className="add-selected-btn"
                                    onClick={handleAddSelected}
                                    disabled={loading || selected.size === 0}
                                >
                                    {loading ? '⏳ Adding...' : `Add ${selected.size} selected`}
                                </button>
                            </div>
                        )}

                        {loading && suggestions.length === 0 && (
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
                            placeholder="Describe what you need to do..."
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
