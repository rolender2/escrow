"use client";
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';

interface Escrow {
    id: string;
    buyer_id: string;
    provider_id: string;
    total_amount: number;
    state: string;
}

export default function Dashboard() {
    const { token } = useAuth(); // Auth
    const [escrows, setEscrows] = useState<Escrow[]>([]);
    const [loading, setLoading] = useState(true);
    const [showResetModal, setShowResetModal] = useState(false);

    const refreshData = async () => {
        try {
            const headers: any = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const res = await fetch('http://localhost:8000/escrows', { headers });
            if (res.ok) {
                const data = await res.json();
                setEscrows(data);
            }
        } catch (err) {
            console.error(err);
        }
        setLoading(false);
    };

    useEffect(() => {
        refreshData();
    }, [token]); // Refresh when token changes

    const handleReset = async () => {
        try {
            const headers: any = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;

            await fetch('http://localhost:8000/reset', {
                method: 'POST',
                headers
            });
            window.location.reload();
        } catch (e) {
            console.error(e);
            alert("Failed to reset");
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans relative">
            <div className="max-w-6xl mx-auto">
                <header className="mb-8 flex items-center justify-between">
                    <div>
                        <Link href="/dashboard" className="flex items-center gap-2 group">
                            <span className="text-3xl group-hover:scale-110 transition">🏠</span>
                            <h1 className="text-3xl font-bold text-gray-900 group-hover:text-blue-600 transition">Repair Escrow</h1>
                        </Link>
                        <p className="text-gray-500">Manage your real estate post-inspection holdbacks.</p>
                    </div>

                    <div className="space-x-4 flex items-center">
                        <button
                            onClick={() => setShowResetModal(true)}
                            className="text-red-600 hover:text-red-800 font-medium text-sm transition-colors border border-red-200 px-3 py-1.5 rounded bg-red-50"
                        >
                            Reset System
                        </button>
                        <Link href="/audit" className="text-gray-600 hover:text-gray-900 font-medium transition-colors">
                            View Ledger
                        </Link>
                        <Link href="/create" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg shadow-sm font-medium transition-colors">
                            + New Repair Escrow
                        </Link>
                    </div>
                </header>

                {loading ? (
                    <div className="text-center py-20 text-gray-400">Loading escrows...</div>
                ) : escrows.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
                        <p className="text-gray-500 mb-4">No active escrows found.</p>
                        <Link href="/create" className="text-blue-600 font-medium hover:underline">Create your first agreement &rarr;</Link>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {escrows.map(escrow => (
                            <Link key={escrow.id} href={`/escrow/${escrow.id}`}>
                                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition cursor-pointer group">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 font-bold group-hover:bg-blue-100 transition">
                                            $
                                        </div>
                                        <span className={cn(
                                            "px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wide",
                                            escrow.state === 'CREATED' ? "bg-amber-100 text-amber-700" :
                                                escrow.state === 'FUNDED' ? "bg-blue-100 text-blue-700" :
                                                    escrow.state === 'ACTIVE' ? "bg-emerald-100 text-emerald-700" :
                                                        "bg-gray-100 text-gray-700"
                                        )}>
                                            {escrow.state}
                                        </span>
                                    </div>
                                    <h3 className="font-semibold text-gray-900 mb-1">{escrow.id.slice(0, 8)}...</h3>
                                    <p className="text-sm text-gray-500 mb-4">Buyer: {escrow.buyer_id}</p>
                                    <div className="pt-4 border-t border-gray-100 flex justify-between items-center">
                                        <span className="text-2xl font-bold text-gray-900">${escrow.total_amount?.toLocaleString()}</span>
                                        <span className="text-sm text-gray-400">View Details &rarr;</span>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>

            {/* Reset Confirmation Modal */}
            {showResetModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-in fade-in zoom-in duration-200">
                        <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mb-4 mx-auto">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                        </div>
                        <h3 className="text-xl font-bold text-center text-gray-900 mb-2">Reset System?</h3>
                        <p className="text-center text-gray-500 mb-6">
                            This action is <span className="font-bold text-red-600">irreversible</span>. It will wipe all Escrows, Milestones, Evidence, and the entire Audit Ledger.
                        </p>
                        <div className="grid grid-cols-2 gap-4">
                            <button
                                onClick={() => setShowResetModal(false)}
                                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleReset}
                                className="px-4 py-2 rounded-lg bg-red-600 text-white font-bold hover:bg-red-700 shadow-md hover:shadow-lg transition"
                            >
                                Yes, Wipe Everything
                            </button>
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}
