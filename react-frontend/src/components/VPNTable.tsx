import React, { useState } from "react";
import { Download, QrCode } from "lucide-react";

export type VPNTableEntry = {
    region: string | null;
    ipv4: string;
    status: string;
    onQrCodeClick: () => void;
    onDownloadClick: () => void;
};

type VPNTableData = {
    data: VPNTableEntry[];
    isAdmin: boolean;
    onStatusChange?: (index: number, newStatus: string) => void;
};

const VPNTable: React.FC<VPNTableData> = ({ data, isAdmin, onStatusChange }) => {
    const actionOptions: Record<string, string> = {
        "Running": "Start", 
        "Paused": "Pause"
    };

    return (
        <div className="bg-white mt-8 p-6 rounded-2xl shadow-lg w-full max-w-4xl">
            <h2 className="text-2xl font-semibold text-center mb-6">VPN Instances</h2>
            {/* {actions && 
                <button 
                    // onClick={handleApplyActions} 
                    className={"w-full p-3 rounded-lg transition cursor-pointer bg-blue-600 text-white hover:bg-blue-700"}
                    >
                        Apply
                </button>
            } */}
            <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-left text-gray-700">
                    <thead className="border-b border-gray-200 text-gray-900">
                        <tr>
                            <th className="px-4 py-2">Region</th>
                            <th className="px-4 py-2">Address</th>
                            <th className="px-4 py-2">Status</th>
                            <th className="px-4 py-2 text-center">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((entry, index) => (
                            <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="px-4 py-2">{entry.region || "Null"}</td>
                                <td className="px-4 py-2">{entry.ipv4}</td>
                                <td className="px-4 py-2">{entry.status}</td>
                                <td className="px-4 py-2 flex justify-center space-x-4">
                                    {isAdmin ? (
                                        <select
                                            onChange={(e) =>
                                                onStatusChange?.(index, e.target.value)
                                            }
                                            className="p-2 border rounded-lg focus:ring-blue-500 focus:outline-none"
                                        >
                                            <option value="" selected>{actionOptions[entry.status]}</option>
                                            {Object.entries(actionOptions).map(([status, action]) => {
                                                return status.toLowerCase() !== entry.status.toLowerCase() &&
                                                    <option 
                                                        key={status} 
                                                        value={action}
                                                    >
                                                        {action}
                                                    </option>
                                            })}
                                        </select>
                                    ) : (
                                        entry.status
                                    )}
                                    <button
                                        onClick={entry.onQrCodeClick}
                                        className="text-blue-600 hover:text-blue-800"
                                    >
                                        <QrCode size={20} />
                                    </button>
                                    <button
                                        onClick={entry.onDownloadClick}
                                        className="text-green-600 hover:text-green-800"
                                    >
                                        <Download size={20} />
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

export default VPNTable;
