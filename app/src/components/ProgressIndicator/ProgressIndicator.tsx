"use client";

import { WorkflowStep } from "@/types";

interface ProgressIndicatorProps {
  currentStep: string;
  progress: number;
  steps: WorkflowStep[];
}

export function ProgressIndicator({
  currentStep,
  progress,
  steps,
}: ProgressIndicatorProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Processing Progress</h3>
        <span className="text-sm text-gray-600">{Math.round(progress * 100)}%</span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${progress * 100}%` }}
        ></div>
      </div>

      {/* Current Step */}
      <div className="text-center">
        <p className="text-gray-700 font-medium">{currentStep}</p>
      </div>

      {/* Workflow Steps */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {steps.map((step, index) => (
          <div
            key={step.name}
            className={`flex flex-col items-center p-3 rounded-lg border-2 transition-all duration-200 ${
              index < steps.length * progress
                ? "border-primary-200 bg-primary-50"
                : "border-gray-200 bg-gray-50"
            }`}
          >
            <span className="text-2xl mb-2">{step.emoji}</span>
            <h4 className="text-sm font-semibold text-gray-900 text-center">
              {step.name}
            </h4>
            <p className="text-xs text-gray-600 text-center mt-1">{step.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
