"use client";
import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
    const { login } = useAuth();
    const router = useRouter();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('password123'); // Default for MVP
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const res = await fetch('http://localhost:8000/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            if (!res.ok) throw new Error('Invalid credentials');

            const data = await res.json();
            login(data.access_token);
            router.push('/dashboard');
        } catch (err: any) {
            setError(err.message);
        }
    };

    const quickFill = (user: string) => {
        setUsername(user);
        setPassword("password123");
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100 font-sans">
            <div className="bg-white p-8 rounded-xl shadow-lg max-w-sm w-full">
                <h1 className="text-2xl font-bold mb-6 text-center text-gray-900">Sign In</h1>

                {error && <div className="bg-red-50 text-red-600 p-3 rounded mb-4 text-sm">{error}</div>}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Username</label>
                        <input
                            type="text"
                            className="w-full mt-1 p-2 border rounded focus:ring-2 focus:ring-blue-500 outline-none text-gray-900"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Password</label>
                        <input
                            type="password"
                            className="w-full mt-1 p-2 border rounded focus:ring-2 focus:ring-blue-500 outline-none text-gray-900"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded font-bold hover:bg-blue-700 transition">
                        Login
                    </button>
                </form>

                <div className="mt-8 pt-6 border-t border-gray-100">
                    <p className="text-xs text-gray-400 mb-2 font-medium uppercase text-center">Quick Login (Test Harness)</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <button onClick={() => quickFill("alice_agent")} className="bg-gray-50 hover:bg-blue-50 p-2 rounded text-left">
                            <span className="font-bold text-gray-900 block">Agent</span>
                            <span className="text-gray-500">Alice</span>
                        </button>
                        <button onClick={() => quickFill("rick_contractor")} className="bg-gray-50 hover:bg-green-50 p-2 rounded text-left">
                            <span className="font-bold text-gray-900 block">Contractor</span>
                            <span className="text-gray-500">Rick</span>
                        </button>
                        <button onClick={() => quickFill("rob_inspector")} className="bg-gray-50 hover:bg-purple-50 p-2 rounded text-left">
                            <span className="font-bold text-gray-900 block">Inspector</span>
                            <span className="text-gray-500">Rob</span>
                        </button>
                        <button onClick={() => quickFill("title_co")} className="bg-gray-50 hover:bg-amber-50 p-2 rounded text-left">
                            <span className="font-bold text-gray-900 block">Custodian</span>
                            <span className="text-gray-500">TitleCo</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
