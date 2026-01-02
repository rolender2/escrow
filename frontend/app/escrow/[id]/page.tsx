"use client";
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

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
    version: number;
    agreement_hash: string;
    total_amount: number;
    funded_amount: number;
    milestones: Milestone[];
}

export default function EscrowDetail() {
    const params = useParams();
    const router = useRouter(); // Use correct import from next/navigation
    const { token, user } = useAuth(); // Auth

    const [escrow, setEscrow] = useState<Escrow | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [uploadUrl, setUploadUrl] = useState("http://example.com/photo.jpg");
    const [showBudgetModal, setShowBudgetModal] = useState(false);
    const [showCancelModal, setShowCancelModal] = useState<string | null>(null); // Milestone ID to cancel

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
        if (!token) return setError("Please Login to perform this action.");

        const res = await fetch(`http://localhost:8000/milestones/${milestoneId}/evidence`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ evidence_type: type, url: uploadUrl })
        });

        if (!res.ok) {
            const err = await res.json();
            setError(err.detail);
        } else {
            refreshData();
        }
    };

    const handleApprove = async (milestoneId: string) => {
        setError(null);
        if (!token) return setError("Please Login to perform this action.");

        const res = await fetch(`http://localhost:8000/milestones/${milestoneId}/approve`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                approver_id: "ignored", // Backend uses Token
                signature: "valid_sig"
            })
        });

        if (!res.ok) {
            const err = await res.json();
            setError(err.detail);
        } else {
            refreshData();
        }
    };

    const handleConfirmFunds = async () => {
        setError(null);
        if (!token) return setError("Please Login to perform this action.");

        const res = await fetch(`http://localhost:8000/escrows/${params.id}/confirm_funds`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                custodian_id: "ignored", // Backend uses Token
                confirmation_code: "WIRE_123"
            })
        });

        if (!res.ok) {
            const err = await res.json();
            setError(err.detail);
        } else {
            refreshData();
        }
    };


    const confirmBudgetChange = async () => {
        if (!escrow || !token) return;
        setLoading(true);

        const res = await fetch(`http://localhost:8000/escrows/${params.id}/change-budget`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                amount_delta: 15000, // Hardcoded V1 mock value as per directive example
                milestone_name: "Change Order – Electrical Upgrade",
                evidence_type: "Invoice"
            })
        });

        if (!res.ok) {
            const err = await res.json();
            setError(err.detail);
            setLoading(false);
            setShowBudgetModal(false);
        } else {
            setShowBudgetModal(false);
            refreshData();
        }
    };

    const handleRaiseDispute = async (milestoneId: string) => {
        setError(null);
        if (!token) return setError("Please Login to perform this action.");

        const res = await fetch(`http://localhost:8000/milestones/${milestoneId}/dispute`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            }
        });
        if (!res.ok) {
            const err = await res.json();
            setError(err.detail);
        } else {
            refreshData();
        }
    };

    const handleResolveDispute = async (milestoneId: string, resolution: "RESUME" | "CANCEL") => {
        setError(null);
        if (!token) return setError("Please Login to perform this action.");

        const res = await fetch(`http://localhost:8000/milestones/${milestoneId}/resolve-dispute`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ resolution })
        });
        if (!res.ok) {
            const err = await res.json();
            setError(err.detail);
        } else {
            refreshData();
        }
    };

    if (loading || !escrow) return <div className="p-8">Loading...</div>;

    // Calculate Funding Progress
    const fundedAmount = escrow.funded_amount || 0;
    const isFullyFunded = fundedAmount >= escrow.total_amount;

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <div className="max-w-4xl mx-auto">
                <div className="mb-6">
                    <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 font-medium flex items-center gap-2 transition-colors">
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
                            <div className="flex items-center gap-3 mb-2">
                                <h1 className="text-2xl font-bold text-gray-900">Escrow: {escrow.id.slice(0, 8)}...</h1>
                                <span className="bg-purple-100 text-purple-700 text-xs font-bold px-2 py-0.5 rounded border border-purple-200">
                                    v{escrow.version}
                                </span>
                            </div>

                            <div className="font-mono text-xs text-gray-400 mb-4 bg-gray-50 p-1.5 rounded inline-block">
                                Hash: {escrow.agreement_hash}
                            </div>

                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div><span className="text-gray-500">Buyer:</span> <span className="font-semibold">{escrow.buyer_id}</span></div>
                                <div><span className="text-gray-500">Provider:</span> <span className="font-semibold">{escrow.provider_id}</span></div>
                                <div>
                                    <span className="text-gray-500">State:</span> <span className="font-bold text-blue-600">{escrow.state}</span>
                                </div>
                            </div>

                            <div className="mt-2 text-sm space-y-1">
                                <div>
                                    <span className="text-gray-500">Funding:</span>
                                    <span className={`font-mono font-bold ml-2 ${isFullyFunded ? 'text-green-600' : 'text-amber-600'}`}>
                                        ${fundedAmount.toLocaleString()} / ${escrow.total_amount.toLocaleString()}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-500">Funding Status:</span>
                                    {fundedAmount === 0 ? (
                                        <span className="ml-2 px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700 border border-red-200">
                                            Not Funded
                                        </span>
                                    ) : !isFullyFunded ? (
                                        <span className="ml-2 px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-700 border border-amber-200">
                                            Partial Funding
                                        </span>
                                    ) : (
                                        <span className="ml-2 px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-700 border border-green-200">
                                            Fully Funded
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="text-right space-y-3">
                            {user?.role === 'AGENT' && (
                                <div className="flex gap-2">
                                    <button onClick={() => setShowBudgetModal(true)} className="bg-black text-white px-4 py-2 rounded-lg text-xs font-bold border border-black hover:bg-gray-800 transition shadow-sm">
                                        Change Budget / Funding
                                    </button>
                                </div>
                            )}

                            {/* Show Confirm Button if NOT fully funded (Initial or Delta) */}
                            {!isFullyFunded && (
                                <div>
                                    <p className="text-sm text-amber-600 font-medium mb-1">⚠ Funding Required</p>
                                    <button onClick={handleConfirmFunds} className="bg-amber-100 text-amber-800 px-4 py-2 rounded-lg text-sm font-bold border border-amber-200 hover:bg-amber-200 transition">
                                        (Simulate) Confirm Funds
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Milestones */}
                <h2 className="text-xl font-bold mb-4">Milestones</h2>
                <div className="space-y-4">
                    {escrow.milestones.map(ms => (
                        <div key={ms.id} className={`bg-white p-6 rounded-xl border shadow-sm ${ms.status === 'CREATED' ? 'border-amber-300 bg-amber-50' : 'border-gray-200'}`}>
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-bold">
                                    {ms.name} (${ms.amount})
                                    {ms.status === 'CREATED' && <span className="ml-2 text-xs text-amber-600 font-normal italic">(Waiting for Funding)</span>}
                                </h3>
                                <div>
                                    {ms.status === 'DISPUTED' ? (
                                        <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs font-bold border border-red-200 shadow-sm animate-pulse">DISPUTED</span>
                                    ) : (
                                        <span className="px-3 py-1 bg-gray-100 rounded-full text-xs font-bold">{ms.status}</span>
                                    )}
                                </div>
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
                                                {!hasUploaded && ms.status !== 'CREATED' && ms.status !== 'DISPUTED' && (
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
                                {ms.status === 'EVIDENCE_SUBMITTED' && user?.role === 'INSPECTOR' && (
                                    <button onClick={() => handleApprove(ms.id)} className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700">
                                        Approve Release
                                    </button>
                                )}
                                {(ms.status === 'APPROVED' || ms.status === 'PAID') && (
                                    <button className="bg-gray-100 text-gray-400 px-4 py-2 rounded-lg cursor-not-allowed">
                                        Funds Released
                                    </button>
                                )}

                                {/* Dispute Controls */}
                                {(ms.status === 'PENDING' || ms.status === 'EVIDENCE_SUBMITTED') &&
                                    ['AGENT', 'INSPECTOR', 'CUSTODIAN'].includes(user?.role || '') && (
                                        <button onClick={() => handleRaiseDispute(ms.id)} className="bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700">
                                            Raise Dispute
                                        </button>
                                    )}

                                {ms.status === 'DISPUTED' &&
                                    ['AGENT', 'INSPECTOR', 'CUSTODIAN'].includes(user?.role || '') && (
                                        <div className="flex gap-2">
                                            <button onClick={() => handleResolveDispute(ms.id, 'RESUME')} className="bg-white border border-green-600 text-green-700 px-4 py-2 rounded-lg font-bold hover:bg-green-50 shadow-sm">
                                                Resume Milestone
                                            </button>
                                            <button onClick={() => setShowCancelModal(ms.id)} className="bg-red-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-red-700 shadow-sm">
                                                Cancel Milestone
                                            </button>
                                        </div>
                                    )}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Budget Change Modal */}
                {
                    showBudgetModal && (
                        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden border border-gray-100 scale-100 animate-in zoom-in-95 duration-200">
                                <div className="p-6">
                                    <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mb-4 mx-auto">
                                        <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                                    </div>
                                    <h3 className="text-xl font-bold text-center text-gray-900 mb-2">Increase Project Budget</h3>
                                    <p className="text-gray-500 text-center text-sm mb-6">
                                        You are adding new funds to this project.
                                        <br /><br />
                                        <strong>What happens next:</strong>
                                        <ul className="text-left list-disc ml-5 mt-2 space-y-1">
                                            <li>A new milestone will be created for the added amount</li>
                                            <li>Previously approved and paid work is NOT affected</li>
                                            <li className="text-amber-600 font-bold">New funds will remain locked until re-confirmed by the Client</li>
                                        </ul>
                                    </p>

                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => setShowBudgetModal(false)}
                                            className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={confirmBudgetChange}
                                            className="flex-1 px-4 py-2 bg-black hover:bg-gray-800 text-white font-bold rounded-lg shadow-lg hover:shadow-xl transition-all"
                                        >
                                            Add New Funding
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
                }

                {/* Cancel Milestone Modal */}
                {
                    showCancelModal && (
                        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden border border-gray-100 scale-100 animate-in zoom-in-95 duration-200">
                                <div className="p-6">
                                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 mx-auto">
                                        <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                                    </div>
                                    <h3 className="text-xl font-bold text-center text-gray-900 mb-2">Cancel Milestone?</h3>
                                    <p className="text-gray-500 text-center text-sm mb-6">
                                        Are you sure you want to permanently cancel this milestone?
                                        <br /><br />
                                        <strong>Repercussions:</strong>
                                        <ul className="text-left list-disc ml-5 mt-2 space-y-1">
                                            <li className="text-red-600 font-bold">This action is irreversible.</li>
                                            <li>The milestone status will be set to <strong>CANCELLED</strong>.</li>
                                            <li>Any funds allocated to this milestone will remain in the escrow balance but will be permanently inactive.</li>
                                        </ul>
                                    </p>

                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => setShowCancelModal(null)}
                                            className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
                                        >
                                            Back
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (showCancelModal) {
                                                    handleResolveDispute(showCancelModal, 'CANCEL');
                                                    setShowCancelModal(null);
                                                }
                                            }}
                                            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-lg hover:shadow-xl transition-all"
                                        >
                                            Confirm Cancellation
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
                }
            </div >
        </div >
    );
}
