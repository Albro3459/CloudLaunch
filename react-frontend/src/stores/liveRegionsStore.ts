// import { create } from 'zustand';
// import { getLiveRegions, Region } from '../helpers/regionsHelper';

// interface LiveRegionsStore {
//   liveRegions: Region[] | null;
//   loading: boolean;
//   error: string | null;
//   fetchLiveRegions: () => Promise<void>;
//   clearLiveRegions: () => void;
// }

// export const useLiveRegionsStore = create<LiveRegionsStore>((set) => ({
//   liveRegions: null,
//   loading: false,
//   error: null,

//   fetchLiveRegions: async () => {
//     set({ loading: true, error: null });

//     const result = await getLiveRegions();

//     if (result) {
//       set({ liveRegions: result, loading: false });
//     } else {
//       set({ error: 'Live Regions Fetch failed', loading: false });
//     }
//   },

//   clearLiveRegions: () => {
//     set({ liveRegions: null, error: null, loading: false });
//   },
// }));

export {};
