import { createContext, useContext, useMemo, useState, ReactNode } from 'react';
import { api, LoginResponse } from '../api/client';

interface AuthState {
  officerId: string | null;
  name: string | null;
  role: string | null;
  token: string | null;
}

interface AuthCtx extends AuthState {
  login: (officerId: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | undefined>(undefined);

function read(): AuthState {
  return {
    token: localStorage.getItem('token'),
    officerId: localStorage.getItem('officerId'),
    name: localStorage.getItem('name'),
    role: localStorage.getItem('role'),
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(read());

  const value = useMemo<AuthCtx>(
    () => ({
      ...state,
      async login(officerId, password) {
        const { data } = await api.post<LoginResponse>('/auth/login', { officerId, password });
        localStorage.setItem('token', data.token);
        localStorage.setItem('officerId', data.officerId);
        localStorage.setItem('name', data.name);
        localStorage.setItem('role', data.role);
        setState(read());
      },
      logout() {
        localStorage.clear();
        setState(read());
      },
    }),
    [state],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAuth outside provider');
  return c;
}
