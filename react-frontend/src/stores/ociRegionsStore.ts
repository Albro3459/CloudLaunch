import { create } from 'zustand';
import { oci_regions, Region } from '../helpers/regionsHelper';
import { SecureGetRegionsHelper } from '../helpers/APIHelper';

interface OciRegionsStore {
  ociRegions: Region[] | null;
  loading: boolean;
  error: string | null;
  fetchOciRegions: (token: string) => Promise<void>;
  clearOciRegions: () => void;
}

let activeFetch: Promise<void> | null = null;

export const fetchOciRegions = async (token: string) : Promise<void> => {
  const store = useOciRegionsStore.getState();
  if (activeFetch) return activeFetch;
  if (store.loading || store.ociRegions?.length) return;
  
  activeFetch = store.fetchOciRegions(token);

  try {
    await activeFetch;
  } finally {
    activeFetch = null;
  }
};

export const useOciRegionsStore = create<OciRegionsStore>((set) => ({
  ociRegions: null,
  loading: false,
  error: null,

  fetchOciRegions: async (token: string) => {
    set({ loading: true, error: null });

    const result = await SecureGetRegionsHelper(token);

    if (result?.success) {
      const ociRegion = result.data?.oci_region;
      const ociRegionName = result.data?.oci_region_name;
      const fallbackRegion = oci_regions[0];
      const regions: Region[] = [{
        value: ociRegion || fallbackRegion.value,
        name: ociRegionName || fallbackRegion.name
      }];

      set({ ociRegions: regions, loading: false });
    } else {
      set({ error: result?.error || 'OCI regions fetch failed', loading: false });
    }
  },

  clearOciRegions: () => {
    set({ ociRegions: null, error: null, loading: false });
  },
}));
