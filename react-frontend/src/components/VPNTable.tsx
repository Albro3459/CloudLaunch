import React, { useState } from "react";
import { QrCode } from "lucide-react";
import { Targets } from "../helpers/APIHelper";
import { TOGGLE } from "../pages/Home";
import { getRegionName } from "../helpers/regionsHelper";

export type VPNTableEntry = {
    userID: string;
    email: string | null;
    region: string | null;
    instanceID: string;
    ipv4: string;
    status: string;
    onQrCodeClick: () => void;
};

type VPNTableData = {
    data: VPNTableEntry[];
    isAdmin: boolean;
    targets: Targets;
    toggleTarget: (toggle: TOGGLE, userID: string, region: string | null, instanceID: string) => void;
    actionFunc: (targets: Targets) => void;
};

const capitalized = (str: string) => {
    return str[0].toUpperCase() + str.slice(1).toLowerCase();
};

const sortedData = (data: VPNTableEntry[], sortField: string | null, sortAsc: boolean) => {
    return [...data].sort((a, b) => {
        if (!sortField) return 0;
        
        let aVal = a[sortField as keyof VPNTableEntry];
        let bVal = b[sortField as keyof VPNTableEntry];

        if (sortField === "region") {
            aVal = getRegionName(aVal as string | null) || "";
            bVal = getRegionName(bVal as string | null) || "";
        } else {
            aVal = aVal || "";
            bVal = bVal || "";
        }

        return sortAsc
            ? String(aVal).localeCompare(String(bVal))
            : String(bVal).localeCompare(String(aVal));
    });
};

export const VPNTable: React.FC<VPNTableData> = ({ data, isAdmin, targets, toggleTarget, actionFunc }) => {

    const [showConfirm, setShowConfirm] = useState(false);

    const [sortField, setSortField] = useState<string | null>(null);
    const [sortAsc, setSortAsc] = useState(true);

    const handleSort = (field: string) => {
        if (sortField === field) {
            setSortAsc(!sortAsc);
        } else {
            setSortField(field);
            setSortAsc(true);
        }
    };

    return (
        <div className="bg-white mt-8 p-6 rounded-2xl shadow-lg w-full max-w-4xl relative">
            <div className="text-center relative mb-4 mt-2">
                <h2 className="text-2xl font-semibold">VPN Instances</h2>
                {isAdmin && targets && Object.keys(targets).length > 0 && (
                <>
                    <button
                        onClick={() => setShowConfirm(true)}
                        className="absolute top-0 right-0 p-2 rounded-lg transition cursor-pointer bg-red-600 text-white hover:bg-red-700"
                    >
                        Terminate
                    </button>

                    {showConfirm && (
                        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
                            <div className="bg-white p-6 rounded-xl shadow-lg max-w-sm w-full text-center">
                                <h3 className="text-lg font-semibold mb-4">
                                    Confirm Termination
                                </h3>
                                <p className="mb-6 text-sm text-gray-600">
                                    Are you sure you want to terminate the selected instances?
                                </p>
                                <div className="flex justify-center gap-4">
                                    <button
                                        onClick={() => {
                                            actionFunc(targets);
                                            setShowConfirm(false);
                                        }}
                                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                                    >
                                        Yes, Terminate
                                    </button>
                                    <button
                                        onClick={() => setShowConfirm(false)}
                                        className="px-4 py-2 bg-gray-300 text-gray-800 rounded-lg hover:bg-gray-400 transition"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            </div>
            
            <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-left text-gray-700">
                    <thead className="border-b border-gray-200 text-gray-900">
                        <tr>
                            {isAdmin &&
                                <>
                                    <th className="px-4 py-2 text-center">Terminate</th>
                                    <th 
                                        className="px-4 py-2 text-center"
                                        onClick={() => handleSort("email")}
                                    >
                                        User
                                    </th>
                                </>
                            }
                            <th 
                                className="px-4 py-2 text-center"
                                onClick={() => handleSort("region")}
                            >
                                Region
                            </th>
                            <th className="px-4 py-2 text-center">Address</th>
                            <th className="px-4 py-2 text-center">Status</th>
                            <th className="px-4 py-2 text-center">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sortedData(data, sortField, sortAsc).map((entry, index) => (
                            <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                                {isAdmin &&
                                    <>
                                        <td className="px-4 py-4 flex justify-center items-center">
                                        <input 
                                            type="checkbox"
                                            checked={targets?.[entry.userID]?.[entry.region || ""]?.includes(entry.instanceID) || false}
                                            onChange={(e) => toggleTarget(e.target.checked ? TOGGLE.ADD : TOGGLE.REMOVE, entry.userID, entry.region, entry.instanceID) }
                                        />
                                        </td>
                                        <td className="px-4 py-2 text-center">{entry.email || "Null"}</td>
                                    </>
                                }
                                <td className="px-4 py-2 text-center">{getRegionName(entry.region) || "Null"}</td>
                                <td className="px-4 py-2 text-center">{entry.ipv4}</td>
                                <td className="px-4 py-2 text-center">{capitalized(entry.status)}</td>
                                <td className="px-4 py-2 flex justify-center">
                                    <button
                                        onClick={entry.onQrCodeClick}
                                        className="text-blue-600 hover:text-blue-800"
                                    >
                                        <QrCode size={20} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};