import { create } from 'zustand';
import { SecureGetHelper } from '../helpers/APIHelper';

interface KeyStore {
  keys: Record<string, any> | null;
  loading: boolean;
  error: string | null;
  fetchKeys: (requestedKeys: string[], token: string) => Promise<void>;
  clearKeys: () => void;
}

let activeFetch: Promise<void> | null = null;

export const fetchKeys = async (requestedKeys: string[], token: string) : Promise<void> => {
  const store = useKeyStore.getState();
  if (activeFetch) return activeFetch; // Consumer can wait on the original fetch!!!
  if (store.loading || store.keys) return;
  
  activeFetch = store.fetchKeys(requestedKeys, token);

  try {
    await activeFetch;
  } finally {
    activeFetch = null;
  }
};

export const useKeyStore = create<KeyStore>((set, get) => ({
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
