"use client";
import React, { useEffect, useState } from 'react';
import Link from 'next/link';

interface AuditLog {
    entity_id: string;
    event_type: string;
    actor_id: string;
    event_data: any;
    timestamp: string;
    previous_hash: string;
    current_hash: string;
}

export default function AuditExplorer() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:8000/audit-logs')
            .then(res => res.json())
            .then(data => { setLogs(data); setLoading(false); })
            .catch(err => console.error(err));
    }, []);

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <header className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Tamper-Evident Audit Trail</h1>
                    <p className="text-gray-500">Tamper-evident audit trail of all system events.</p>
                </div>
                <Link href="/" className="text-blue-600 font-medium hover:underline">
                    &larr; Back to Dashboard
                </Link>
            </header>

            {loading ? (
                <div className="text-center py-20 text-gray-400">Loading ledger...</div>
            ) : (
                <div className="space-y-4">
                    {logs.map((log, i) => (
                        <div key={i} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm font-mono text-sm relative overflow-hidden">
                            {/* Chain Link Visual */}
                            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>

                            <div className="flex justify-between items-start mb-2">
                                <span className="font-bold text-lg text-blue-700">{log.event_type}</span>
                                <span className="text-gray-400 text-xs">{new Date(log.timestamp).toLocaleString()}</span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-600">
                                <div>
                                    <p><span className="font-semibold text-gray-900">Entity:</span> {log.entity_id}</p>
                                    <p><span className="font-semibold text-gray-900">Actor:</span> {log.actor_id}</p>
                                    <div className="mt-2 p-2 bg-gray-50 rounded border border-gray-100 max-h-20 overflow-auto">
                                        <pre>{JSON.stringify(log.event_data, null, 2)}</pre>
                                    </div>
                                </div>
                                <div className="break-all">
                                    <p className="text-green-600 mb-1">
                                        <span className="font-bold">Current Hash:</span><br />
                                        {log.current_hash}
                                    </p>
                                    <p className="text-gray-400">
                                        <span className="font-bold">Prev Hash:</span><br />
                                        {log.previous_hash}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
