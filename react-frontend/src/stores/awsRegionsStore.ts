import { create } from 'zustand';
import { getRegionName, Region } from '../helpers/regionsHelper';
import { SecureGetRegionsHelper } from '../helpers/APIHelper';

interface AWSRegionsStore {
  AWSRegions: Region[] | null;
  loading: boolean;
  error: string | null;
  fetchAWSRegions: (token: string) => Promise<void>;
  clearAWSRegions: () => void;
}

let activeFetch: Promise<void> | null = null;

export const fetchAWSRegions = async (token: string) : Promise<void> => {
  const store = useAWSRegionsStore.getState();
  if (activeFetch) return activeFetch;
  if (store.loading || store.AWSRegions?.length) return;
  
  activeFetch = store.fetchAWSRegions(token);

  try {
    await activeFetch;
  } finally {
    activeFetch = null;
  }
};

export const useAWSRegionsStore = create<AWSRegionsStore>((set) => ({
  AWSRegions: null,
  loading: false,
  error: null,

  fetchAWSRegions: async (token: string) => {
    set({ loading: true, error: null });

    // console.log("FETCHING REGIONS");
    const result = await SecureGetRegionsHelper(token);

    if (result?.success) {
      const regions: Region[] = result?.data?.map((x: string) => {
        const region: Region = {
          value: x,
          name: getRegionName(x)
        }
        return region;
      });

      // console.log("REGIONS FETCHED: ", JSON.stringify(result?.data));

      set({ AWSRegions: regions?.toSorted((a, b) => a.name.localeCompare(b.name)), loading: false });
    } else {
      set({ error: result?.error || 'AWS Regions Fetch failed', loading: false });
    }
  },

  clearAWSRegions: () => {
    set({ AWSRegions: null, error: null, loading: false });
  },
}));