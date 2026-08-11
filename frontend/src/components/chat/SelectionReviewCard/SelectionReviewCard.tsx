"use client";

import { HitlFeedback, HitlRequest } from "@/types";
import { useMemo, useState } from "react";

interface SelectionReviewCardProps {
  request: HitlRequest;
  onSubmit: (feedback: HitlFeedback) => void;
  onCancel?: () => void;
}

export function SelectionReviewCard({
  request,
  onSubmit,
  onCancel,
}: SelectionReviewCardProps) {
  const [selected, setSelected] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const it of request.items) init[it] = true;
    return init;
  });
  const [notes, setNotes] = useState("");

  const approvedItems = useMemo(
    () => Object.keys(selected).filter((k) => selected[k]),
    [selected],
  );

  const toggle = (item: string) => {
    setSelected((prev) => ({ ...prev, [item]: !prev[item] }));
  };

  const handleApprove = () => {
    const payload: HitlFeedback = {
      checkpointId: request.id,
      review_type: request.review_type,
      action: "approve",
      approved_items: request.items,
      feedback_text: notes || undefined,
    };
    onSubmit(payload);
  };

  const handleModify = () => {
    const payload: HitlFeedback = {
      checkpointId: request.id,
      review_type: request.review_type,
      action: "modify",
      approved_items: approvedItems,
      suggested_items: [],
      feedback_text: notes || undefined,
    };
    onSubmit(payload);
  };

  return (
    <div className="border rounded-lg p-4 bg-white shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-gray-900">
          Review {request.review_type === "databases" ? "databases" : "tables"}
        </h3>
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {request.items.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => toggle(item)}
            className={`px-3 py-1.5 text-sm rounded-full border ${
              selected[item]
                ? "bg-black text-white border-black"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="mb-3">
        <textarea
          className="w-full border rounded-md px-3 py-2 text-sm"
          rows={3}
          placeholder={`Optional notes or suggestions (e.g., "add account db", "remove wallet db", "include user table")`}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleApprove}
          className="px-3 py-1.5 text-sm font-medium rounded-md bg-green-600 text-white hover:bg-green-700"
        >
          Approve
        </button>
        <button
          type="button"
          onClick={handleModify}
          className="px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700"
        >
          Apply Selection
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
