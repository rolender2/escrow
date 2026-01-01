"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

export default function Create() {
    const router = useRouter();
    const { token, user } = useAuth(); // Auth Context
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState({
        buyer_id: "",
        provider_id: "",
        amount: "",
        milestone_name: ""
    });

    // Protect Page
    if (!token) {
        if (typeof window !== 'undefined') router.push('/login');
        return null;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        const payload = {
            buyer_id: formData.buyer_id,
            provider_id: formData.provider_id,
            total_amount: parseFloat(formData.amount),
            milestones: [
                {
                    name: formData.milestone_name,
                    amount: parseFloat(formData.amount),
                    required_evidence_types: ["Photo"]
                }
            ]
        };

        const res = await fetch("http://localhost:8000/escrows", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            router.push("/dashboard");
        } else {
            const err = await res.json();
            setError(`Failed: ${err.detail}`);
            // alert(`Failed: ${err.detail}`);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans flex justify-center">
            <div className="w-full max-w-lg bg-white rounded-xl border border-gray-200 shadow-sm p-8">
                <div onClick={() => router.push('/dashboard')} className="cursor-pointer mb-6 flex items-center gap-2">
                    <span className="text-2xl">🏠</span>
                    <h2 className="text-2xl font-bold text-gray-900 hover:text-blue-600 transition">Start Repair Escrow</h2>
                </div>

                {user?.role !== 'AGENT' && (
                    <div className="mb-4 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded text-sm shadow-sm">
                        <p className="font-bold">Access Warning</p>
                        <p>You are logged in as <span className="font-mono bg-red-100 px-1 rounded">{user?.role}</span>. Only AGENTS can create escrows.</p>
                    </div>
                )}

                {/* Error Banner */}
                {error && (
                    <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
                        <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <span className="font-medium">{error}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Buyer (Client)</label>
                        <input
                            required
                            className="w-full p-2 border rounded-lg placeholder-gray-400"
                            placeholder="Buyer Name"
                            value={formData.buyer_id}
                            onChange={e => setFormData({ ...formData, buyer_id: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Service Provider (Contractor)</label>
                        <input
                            required
                            className="w-full p-2 border rounded-lg placeholder-gray-400"
                            placeholder="Contractor Name"
                            value={formData.provider_id}
                            onChange={e => setFormData({ ...formData, provider_id: e.target.value })}
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
                            <input
                                required
                                type="number"
                                className="w-full p-2 border rounded-lg placeholder-gray-400"
                                placeholder="1000"
                                value={formData.amount}
                                onChange={e => setFormData({ ...formData, amount: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Repair Item</label>
                            <input
                                required
                                className="w-full p-2 border rounded-lg placeholder-gray-400"
                                placeholder="Roof Repair - North Wing"
                                value={formData.milestone_name}
                                onChange={e => setFormData({ ...formData, milestone_name: e.target.value })}
                            />
                        </div>
                    </div>

                    <button type="submit" className="w-full mt-6 bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition">
                        Create & Lock Funds
                    </button>
                </form>
            </div>
        </div>
    );
}
