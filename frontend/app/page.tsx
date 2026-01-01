"use client";
import Link from 'next/link';

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-white font-sans">
            {/* Header */}
            <header className="max-w-6xl mx-auto px-6 py-6 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <span className="text-3xl">🏠</span>
                    <span className="text-xl font-bold text-gray-900">Repair Escrow</span>
                </div>
                <div className="space-x-4">
                    <Link href="/login" className="text-gray-600 hover:text-gray-900 font-medium">Log In</Link>
                    <Link href="/login" className="bg-blue-600 text-white px-5 py-2 rounded-full font-bold hover:bg-blue-700 transition">Get Started</Link>
                </div>
            </header>

            {/* Hero Section */}
            <main className="max-w-6xl mx-auto px-6 py-20 text-center">
                <div className="inline-block bg-blue-50 text-blue-700 font-semibold px-4 py-1.5 rounded-full text-sm mb-6">
                    Trusted by 500+ Real Estate Agents
                </div>
                <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-8">
                    Close Now. <span className="text-blue-600">Fix Later.</span>
                </h1>
                <p className="text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
                    The secure, automated platform for managing post-inspection repair holdbacks.
                    Lock funds instantly and release them only when work is verified.
                </p>

                <div className="flex justify-center gap-4">
                    <Link href="/login" className="bg-blue-600 text-white px-8 py-4 rounded-xl font-bold text-lg hover:bg-blue-700 transition shadow-lg hover:shadow-xl hover:-translate-y-1 transform">
                        Start an Escrow
                    </Link>
                    <Link href="/audit" className="bg-white text-gray-700 border border-gray-200 px-8 py-4 rounded-xl font-bold text-lg hover:bg-gray-50 transition shadow-sm">
                        View Public Ledger
                    </Link>
                </div>

                {/* Feature Grid */}
                <div className="grid md:grid-cols-3 gap-8 mt-24 text-left">
                    <div className="p-6 bg-gray-50 rounded-2xl">
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-2xl mb-4">🔒</div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Secure Holdbacks</h3>
                        <p className="text-gray-600">Funds are cryptographically locked. 100% non-custodial instruction generation.</p>
                    </div>
                    <div className="p-6 bg-gray-50 rounded-2xl">
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-2xl mb-4">📸</div>
                        <p className="text-gray-600">Contractors upload photos directly. Inspects approve with one click.</p>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Verified Repairs</h3>
                    </div>
                    <div className="p-6 bg-gray-50 rounded-2xl">
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-2xl mb-4">⚡</div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Instant Closing</h3>
                        <p className="text-gray-600">Don't let a broken roof kill the deal. Create an agreement in 30 seconds.</p>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-gray-100 py-12 mt-20">
                <div className="max-w-6xl mx-auto px-6 text-center text-gray-400">
                    &copy; 2024 Repair Escrow Protocol. All rights reserved.
                </div>
            </footer>
        </div>
    );
}
