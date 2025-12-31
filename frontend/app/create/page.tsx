"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Create() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        buyer_id: "",
        provider_id: "",
        amount: "",
        milestone_name: ""
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
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
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            router.push("/");
        } else {
            alert("Failed to create escrow");
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans flex justify-center">
            <div className="w-full max-w-lg bg-white rounded-xl border border-gray-200 shadow-sm p-8">
                <div onClick={() => router.push('/')} className="cursor-pointer mb-6 flex items-center gap-2">
                    <span className="text-2xl">🏠</span>
                    <h2 className="text-2xl font-bold text-gray-900 hover:text-blue-600 transition">Start Repair Escrow</h2>
                </div>
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
