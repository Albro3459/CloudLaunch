export const oci_regions: Region[] = [
    { name: "San Jose", value: "us-sanjose-1" },
];

export type Region = {
    name: string;
    value: string;
}

export const getRegionName = (region: string | null): string => {
    if (!region) return '';
    return oci_regions.find(r => r.value === region)?.name || region;
};
