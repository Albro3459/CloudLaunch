import { create } from 'zustand';
import { SecureGetHelper } from '../helpers/APIHelper';

interface KeyStore {
  keys: Record<string, any> | null;
  loading: boolean;
  error: string | null;
  fetchKeys: (requestedKeys: string[], token: string) => Promise<void>;
  clearKeys: () => void;
}

export const useKeyStore = create<KeyStore>((set) => ({
  keys: null,
  loading: false,
  error: null,

  fetchKeys: async (requestedKeys, token) => {
    set({ loading: true, error: null });

    const result = await SecureGetHelper(requestedKeys, token);

    if (result.success) {
      set({ keys: result.data, loading: false });
    } else {
      set({ error: result.error || 'Fetch failed', loading: false });
    }
  },

  clearKeys: () => {
    set({ keys: null, error: null, loading: false });
  },
}));
