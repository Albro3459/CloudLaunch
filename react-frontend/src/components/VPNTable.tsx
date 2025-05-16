import React, { useState } from "react";
import { QrCode } from "lucide-react";
import { Targets } from "../helpers/APIHelper";
import { TOGGLE } from "../pages/Home";

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

export const VPNTable: React.FC<VPNTableData> = ({ data, isAdmin, targets, toggleTarget, actionFunc }) => {

    return (
        <div className="bg-white mt-8 p-6 rounded-2xl shadow-lg w-full max-w-4xl relative">
            <div className="text-center relative mb-4 mt-2">
                <h2 className="text-2xl font-semibold">VPN Instances</h2>
                {isAdmin && targets && Object.keys(targets).length > 0 && 
                    <button 
                        onClick={() => {
                            if (confirm("Are you sure you want to terminate selected instances?")) {
                                actionFunc(targets);
                            }
                        }}
                        className="absolute top-0 right-0 p-2 rounded-lg transition cursor-pointer bg-red-600 text-white hover:bg-red-700"
                    >
                        Terminate
                    </button>
                }
            </div>
            
            <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-left text-gray-700">
                    <thead className="border-b border-gray-200 text-gray-900">
                        <tr>
                            {isAdmin &&
                                <>
                                    <th className="px-4 py-2 text-center">Terminate</th>
                                    <th className="px-4 py-2 text-center">User</th>
                                </>
                            }
                            <th className="px-4 py-2 text-center">Region</th>
                            <th className="px-4 py-2 text-center">Address</th>
                            <th className="px-4 py-2 text-center">Status</th>
                            <th className="px-4 py-2 text-center">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((entry, index) => (
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
                                <td className="px-4 py-2 text-center">{entry.region || "Null"}</td>
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