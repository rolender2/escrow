"use client";
import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

interface Evidence {
    evidence_type: string;
    url: string;
}
interface Milestone {
    id: string;
    name: string;
    amount: number;
    required_evidence_types: string[];
    status: string;
    evidence: Evidence[];
}
interface Escrow {
    id: string;
    buyer_id: string;
    provider_id: string;
    state: string;
    milestones: Milestone[];
}

export default function EscrowDetail() {
    const params = useParams();
    const [escrow, setEscrow] = useState<Escrow | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [uploadUrl, setUploadUrl] = useState("http://example.com/photo.jpg");

    const refreshData = () => {
        fetch(`http://localhost:8000/escrows/${params.id}`)
            .then(res => res.json())
            .then(data => { setEscrow(data); setLoading(false); })
            .catch(err => console.error(err));
    };

    useEffect(() => {
        refreshData();
    }, []);

    const handleUpload = async (milestoneId: string, type: string) => {
        setError(null);
        await fetch(`http://localhost:8000/milestones/${milestoneId}/evidence`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ evidence_type: type, url: uploadUrl })
        });
        refreshData();
    };

    const handleApprove = async (milestoneId: string) => {
        setError(null);
        // 1. Approve
        const res = await fetch(`http://localhost:8000/milestones/${milestoneId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approver_id: "Inspector_Gadget", signature: "valid_sig" })
        });

        if (!res.ok) {
            // User requested specific message for now
            setError("Funds not wired yet.");
            return;
        }

        // 2. Generate Instruction (Triggers status -> PAID)
        try {
            await fetch(`http://localhost:8000/escrows/${params.id}/instruction/${milestoneId}`);
        } catch (e) {
            console.error("Failed to generate instruction", e);
        }

        refreshData();
    };

    const handleConfirmFunds = async () => {
        setError(null);
        await fetch(`http://localhost:8000/escrows/${params.id}/confirm_funds`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ custodian_id: "TitleCompany_X", confirmation_code: "WIRE_123" })
        });
        refreshData();
    };

    if (loading || !escrow) return <div className="p-8">Loading...</div>;

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <div className="max-w-4xl mx-auto">
                <div className="mb-6">
                    <Link href="/" className="text-gray-500 hover:text-gray-900 font-medium flex items-center gap-2 transition-colors">
                        ← Back to Dashboard
                    </Link>
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
                        <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <span className="font-medium">{error}</span>
                    </div>
                )}

                {/* Header */}
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-6">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Escrow: {escrow.id.slice(0, 8)}...</h1>
                            <div className="grid grid-cols-3 gap-4 mt-4 text-sm">
                                <div><span className="text-gray-500">Buyer:</span> <span className="font-semibold">{escrow.buyer_id}</span></div>
                                <div><span className="text-gray-500">Provider:</span> <span className="font-semibold">{escrow.provider_id}</span></div>
                                <div><span className="text-gray-500">State:</span> <span className="font-bold text-blue-600">{escrow.state}</span></div>
                            </div>
                        </div>
                        {escrow.state === 'CREATED' && (
                            <div className="text-right">
                                <p className="text-sm text-amber-600 font-medium mb-2">⚠ Funds NOT Confirmed</p>
                                <button onClick={handleConfirmFunds} className="bg-amber-100 text-amber-800 px-4 py-2 rounded-lg text-sm font-bold border border-amber-200 hover:bg-amber-200 transition">
                                    (Simulate) Confirm Wire Received
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Milestones */}
                <h2 className="text-xl font-bold mb-4">Milestones</h2>
                <div className="space-y-4">
                    {escrow.milestones.map(ms => (
                        <div key={ms.id} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-bold">{ms.name} (${ms.amount})</h3>
                                <span className="px-3 py-1 bg-gray-100 rounded-full text-xs font-bold">{ms.status}</span>
                            </div>

                            {/* Evidence Section */}
                            <div className="mb-4">
                                <h4 className="text-sm font-semibold text-gray-500 uppercase mb-2">Required Evidence</h4>
                                <div className="space-y-2">
                                    {ms.required_evidence_types.map(type => {
                                        const hasUploaded = ms.evidence.some(e => e.evidence_type === type);
                                        return (
                                            <div key={type} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                                                <div className="flex items-center space-x-2">
                                                    <div className={`w-3 h-3 rounded-full ${hasUploaded ? 'bg-green-500' : 'bg-red-300'}`} />
                                                    <span>{type}</span>
                                                </div>
                                                {!hasUploaded && (
                                                    <div className="flex space-x-2">
                                                        <input className="text-xs p-1 border rounded" value={uploadUrl} onChange={e => setUploadUrl(e.target.value)} />
                                                        <button onClick={() => handleUpload(ms.id, type)} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">Upload</button>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="border-t pt-4 flex justify-end space-x-4">
                                {ms.status === 'PENDING' && (
                                    <button disabled className="bg-gray-100 text-gray-400 px-4 py-2 rounded-lg cursor-not-allowed font-medium">
                                        Approve Release
                                    </button>
                                )}
                                {ms.status === 'EVIDENCE_SUBMITTED' && (
                                    <button onClick={() => handleApprove(ms.id)} className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700">
                                        Approve Release
                                    </button>
                                )}
                                {(ms.status === 'APPROVED' || ms.status === 'PAID') && (
                                    <button className="bg-gray-100 text-gray-400 px-4 py-2 rounded-lg cursor-not-allowed">
                                        Funds Released
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
