export const oci_regions: Region[] = [
    { name: "California", value: "us-sanjose-1" },
];

export type Region = {
    name: string;
    value: string;
}

export const getRegionName = (region: string | null, regions: Region[] | null = oci_regions): string => {
    if (!region) return '';
    return (regions || oci_regions).find(r => r.value === region)?.name || region;
};
