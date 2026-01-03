"use client";

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';

interface Notification {
    _id: string;
    message: string;
    event_type: string;
    severity: "INFO" | "ACTION_REQUIRED" | "WARNING";
    is_read: boolean;
    created_at: string;
    escrow_id?: string;
    milestone_id?: string;
}

export default function NotificationBell() {
    const { token } = useAuth();
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const fetchNotifications = async () => {
        if (!token) return;
        try {
            const res = await fetch('http://localhost:8000/notifications', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setNotifications(data);
                setUnreadCount(data.filter((n: Notification) => !n.is_read).length);
            }
        } catch (e) {
            console.error("Failed to fetch notifications", e);
        }
    };

    // Poll every 5 seconds
    useEffect(() => {
        fetchNotifications();
        const interval = setInterval(fetchNotifications, 5000);
        return () => clearInterval(interval);
    }, [token]);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const markAsRead = async (id: string) => {
        if (!token) return;
        try {
            await fetch(`http://localhost:8000/notifications/${id}/read`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            // Optimistic update
            setNotifications(prev => prev.map(n => n._id === id ? { ...n, is_read: true } : n));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (e) {
            console.error("Failed to mark read", e);
        }
    };

    if (!token) return null;

    return (
        <div className="relative mr-6" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-1 text-gray-400 hover:text-white transition-colors"
                title="Notifications"
            >
                {/* SVG Bell Icon */}
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                </svg>

                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm animate-pulse">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown Panel */}
            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl ring-1 ring-black ring-opacity-5 z-50 overflow-hidden text-gray-800">
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-100 flex justify-between items-center">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Notifications</h3>
                        <span className="text-xs text-gray-400">{unreadCount} unread</span>
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="p-4 text-center text-sm text-gray-400">No notifications</div>
                        ) : (
                            notifications.map(n => (
                                <div
                                    key={n._id}
                                    onClick={() => !n.is_read && markAsRead(n._id)}
                                    className={`p-4 border-b border-gray-100 cursor-pointer transition-colors ${n.is_read ? 'bg-white text-gray-500 hover:bg-gray-50' : 'bg-blue-50 text-gray-800 hover:bg-blue-100'}`}
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${n.severity === 'ACTION_REQUIRED' ? 'bg-red-100 text-red-600' :
                                                n.severity === 'WARNING' ? 'bg-amber-100 text-amber-600' :
                                                    'bg-blue-100 text-blue-600'
                                            }`}>
                                            {n.severity.replace('_', ' ')}
                                        </span>
                                        <span className="text-[10px] text-gray-400">
                                            {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                    <p className="text-xs leading-relaxed">{n.message}</p>
                                    <div className="mt-1 flex space-x-2 text-[10px] text-gray-400 font-mono">
                                        {n.escrow_id && <span>#{n.escrow_id.substring(0, 6)}...</span>}
                                        {n.milestone_id && <span>Milestone: {n.milestone_id.substring(0, 4)}...</span>}
                                    </div>
                                    {!n.is_read && <div className="mt-2 text-[10px] text-blue-600 font-semibold">Mark as Read</div>}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
