"use client";
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface User {
    sub: string; // username
    role: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        // Hydrate from localStorage
        const storedToken = localStorage.getItem('access_token');
        if (storedToken) {
            login(storedToken);
        }
    }, []);

    const login = (accessToken: string) => {
        localStorage.setItem('access_token', accessToken);
        setToken(accessToken);

        // Decode simple JWT (Prototype Only - In prod use library)
        try {
            const payload = JSON.parse(atob(accessToken.split('.')[1]));
            setUser({ sub: payload.sub, role: payload.role });
        } catch (e) {
            console.error("Invalid Token");
            logout();
        }
    };

    const logout = () => {
        localStorage.setItem('access_token', '');
        setToken(null);
        setUser(null);
        router.push('/');
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within AuthProvider");
    return context;
};
