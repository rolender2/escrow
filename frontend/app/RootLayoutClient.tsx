"use client";

import { AuthProvider, useAuth } from '@/context/AuthContext'
import React from 'react'

import NotificationBell from './components/NotificationBell';

// Sub-component for session banner to use useAuth hook
function SessionBanner() {
    const { user, logout } = useAuth();
    if (!user) return null;

    return (
        <div className="bg-gray-900 text-white text-xs py-2 px-8 flex justify-between items-center w-full z-50">
            <div className="flex items-center space-x-2">
                <span className="text-gray-400">Logged in as:</span>
                <span className="font-bold font-mono text-green-400">{user.sub}</span>
                <span className="bg-gray-700 px-1.5 rounded text-[10px] uppercase font-bold tracking-wider">{user.role}</span>
            </div>
            <div className="flex items-center">
                <NotificationBell />
                <button onClick={logout} className="text-gray-400 hover:text-white underline">Sign Out</button>
            </div>
        </div>
    )
}

export default function RootLayoutClient({ children }: { children: React.ReactNode }) {
    return (
        <AuthProvider>
            <SessionBanner />
            {children}
        </AuthProvider>
    )
}
