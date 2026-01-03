"use client";
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

export default function Create() {
    const router = useRouter();
    const { token, user } = useAuth();
    const [error, setError] = useState<string | null>(null);
    const [formData, setFormData] = useState({
        buyer_id: "",
        provider_id: "",
        amount: "",
        milestone_name: ""
    });

    // Template State
    const [templates, setTemplates] = useState<any[]>([]);
    const [useTemplate, setUseTemplate] = useState(false);
    const [selectedTemplateId, setSelectedTemplateId] = useState("");

    // Fetch Templates on Mount
    useEffect(() => {
        fetch('http://localhost:8000/templates')
            .then(res => res.json())
            .then(data => setTemplates(data))
            .catch(err => console.error("Failed to fetch templates", err));
    }, []);

    const selectedTemplate = templates.find(t => t.id === selectedTemplateId);

    // Protect Page
    if (!token) {
        if (typeof window !== 'undefined') router.push('/login');
        return null;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // 1. Prepare Payload (Empty milestones if using template)
        const payload = {
            buyer_id: formData.buyer_id,
            provider_id: formData.provider_id,
            total_amount: parseFloat(formData.amount),
            milestones: useTemplate ? [] : [
                {
                    name: formData.milestone_name,
                    amount: parseFloat(formData.amount),
                    required_evidence_types: ["Photo"]
                }
            ]
        };

        try {
            // 2. Create Escrow
            const res = await fetch("http://localhost:8000/escrows", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const escrow = await res.json();

                // 3. Apply Template if selected
                if (useTemplate && selectedTemplateId) {
                    const tRes = await fetch(`http://localhost:8000/escrows/${escrow.id}/apply-template`, {
                        method: 'POST',
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": `Bearer ${token}`
                        },
                        body: JSON.stringify({ template_id: selectedTemplateId })
                    });

                    if (!tRes.ok) {
                        const tErr = await tRes.json();
                        setError(`Escrow created but Template failed: ${tErr.detail}`);
                        return;
                    }
                }
                router.push("/dashboard");
            } else {
                const err = await res.json();
                setError(`Failed: ${err.detail}`);
            }
        } catch (e: any) {
            setError(`Network Error: ${e.message}`);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans flex justify-center">
            <div className="w-full max-w-lg bg-white rounded-xl border border-gray-200 shadow-sm p-8">
                <div onClick={() => router.push('/dashboard')} className="cursor-pointer mb-6 flex items-center gap-2">
                    <span className="text-2xl">🏗️</span>
                    <h2 className="text-2xl font-bold text-gray-900 hover:text-blue-600 transition">Start Construction Escrow</h2>
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

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Total Project Amount ($)</label>
                        <input
                            required
                            type="number"
                            className="w-full p-2 border rounded-lg placeholder-gray-400"
                            placeholder="10000"
                            value={formData.amount}
                            onChange={e => setFormData({ ...formData, amount: e.target.value })}
                        />
                    </div>

                    {/* Template Selection UI */}
                    <div className="border-t border-gray-100 pt-4 mt-4">
                        <div className="flex items-center gap-2 mb-4">
                            <input
                                type="checkbox"
                                id="useTemplate"
                                checked={useTemplate}
                                onChange={e => setUseTemplate(e.target.checked)}
                                className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                            />
                            <label htmlFor="useTemplate" className="text-gray-900 font-medium cursor-pointer">
                                Use a Milestone Template (Recommended)
                            </label>
                        </div>

                        {useTemplate ? (
                            <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg space-y-3 animate-in fade-in slide-in-from-top-2">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Select Template</label>
                                    <select
                                        className="w-full p-2 border rounded-lg bg-white"
                                        value={selectedTemplateId}
                                        onChange={e => setSelectedTemplateId(e.target.value)}
                                        required
                                    >
                                        <option value="">-- Choose a Draw Schedule --</option>
                                        {templates.map(t => (
                                            <option key={t.id} value={t.id}>{t.name}</option>
                                        ))}
                                    </select>
                                </div>

                                {selectedTemplate && (
                                    <div className="text-sm">
                                        <p className="text-gray-600 italic mb-2">{selectedTemplate.description}</p>
                                        <div className="space-y-1">
                                            {selectedTemplate.milestones.map((m: any, idx: number) => (
                                                <div key={idx} className="flex justify-between text-xs bg-white p-2 rounded border border-blue-100">
                                                    <span className="font-medium text-gray-800">{m.title}</span>
                                                    <span className="text-gray-500">
                                                        {m.percentage}%
                                                        {formData.amount && ` ($${(parseFloat(formData.amount) * m.percentage / 100).toLocaleString()})`}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Repair Item (Single Milestone)</label>
                                <input
                                    required
                                    className="w-full p-2 border rounded-lg placeholder-gray-400"
                                    placeholder="Roof Repair - North Wing"
                                    value={formData.milestone_name}
                                    onChange={e => setFormData({ ...formData, milestone_name: e.target.value })}
                                />
                            </div>
                        )}
                    </div>

                    <button type="submit" className="w-full mt-6 bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition">
                        Create & Lock Funds
                    </button>
                </form>
            </div>
        </div>
    );
}
