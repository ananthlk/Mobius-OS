"use client";

import { useState } from "react";
import { 
  Database, CheckCircle2, Brain, Calculator, Sparkles, MessageSquare,
  ChevronDown, ChevronUp, ChevronRight
} from "lucide-react";

export interface ThinkingMessage {
  message: string;
  metadata?: any;
  timestamp: string;
}

export interface ProcessEvent {
  phase: "patient_loading" | "eligibility_check" | "interpretation" | "scoring" | "planning" | "conversation";
  status: "pending" | "in_progress" | "complete" | "error";
  message: string;
  timestamp: string;
  thinking_messages?: ThinkingMessage[];
  data?: {
    patient_summary?: {
      name?: string;
      dob?: string;
      insurance?: string;
      member_id?: string;
    };
    visits?: Array<{
      visit_date?: string;
      visit_type?: string;
      status?: string;
      eligibility_status?: string;
      eligibility_probability?: number;
      event_tense?: string;
    }>;
    score_summary?: {
      probability?: number;
      confidence?: number;
      sample_size?: number;
      confidence_interval?: {
        lower_bound: number;
        upper_bound: number;
      };
    };
    questions_count?: number;
    improvement_plan_count?: number;
    conversation_summary?: string;
    status?: string;
    coverage_start?: string;
    coverage_end?: string;
    product_type?: string;
    plan_name?: string;
    member_id?: string;
    payer_name?: string;
    summary?: string;
    cached?: boolean;
  };
}

interface EligibilityProcessViewProps {
  events: ProcessEvent[];
  isExpanded: boolean;
  onToggle: () => void;
  isStreaming?: boolean;
}

const phaseIcons = {
  patient_loading: Database,
  eligibility_check: CheckCircle2,
  interpretation: Brain,
  scoring: Calculator,
  planning: Sparkles,
  conversation: MessageSquare,
};

const phaseLabels = {
  patient_loading: "Patient EMR Loading",
  eligibility_check: "Eligibility Check",
  interpretation: "Interpretation",
  scoring: "Scoring Engine",
  planning: "Planning",
  conversation: "Conversation Formatting",
};

// Helper component for Patient Information with sub-sections
function PatientInformation({ thinkingMessages, eventData }: { thinkingMessages?: ThinkingMessage[]; eventData?: any }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [emrExpanded, setEmrExpanded] = useState(false);
  const [visitsExpanded, setVisitsExpanded] = useState(false);
  const [eligibilityExpanded, setEligibilityExpanded] = useState(false);
  
  // Extract patient information from thinking messages
  let demographics: any = null;
  let insurance: any = null;
  let visits: any[] = [];
  let eligibility: any = null;
  
  if (thinkingMessages) {
    console.log("🔍 PatientInformation: Received thinking messages:", thinkingMessages.length, thinkingMessages);
    thinkingMessages.forEach((msg, idx) => {
      if (msg.metadata) {
        // Parse metadata if it's a string
        let metadata = msg.metadata;
        if (typeof metadata === 'string') {
          try {
            metadata = JSON.parse(metadata);
          } catch (e) {
            console.warn("⚠️ Failed to parse metadata as JSON:", e, msg.metadata);
            // If parsing fails, skip this message
            return;
          }
        }
        
        const dataType = metadata.data_type;
        console.log(`📦 Thinking message ${idx}: data_type=${dataType}, metadata keys:`, Object.keys(metadata));
        
        // Parse by data_type for structured streaming
        if (dataType === "demographics") {
          demographics = metadata;  // Contains all demographics fields
          console.log("✅ Extracted demographics:", demographics);
        } else if (dataType === "insurance") {
          insurance = metadata;  // Contains all insurance fields
          console.log("✅ Extracted insurance:", insurance);
        } else if (dataType === "visits" && metadata.visits) {
          visits = metadata.visits;  // Contains visits array
          console.log("✅ Extracted visits:", visits.length);
        } else if (dataType === "eligibility") {
          eligibility = metadata;  // Contains all eligibility fields
          console.log("✅ Extracted eligibility:", eligibility);
        }
        // Fallback for old format (no data_type) - backward compatibility
        else if (!dataType) {
          // Old format - check fields directly
          if (metadata.first_name || metadata.last_name || metadata.date_of_birth) {
            demographics = metadata;
            console.log("✅ Extracted demographics (old format):", demographics);
          } else if (metadata.payer_name || metadata.payer_id || metadata.plan_name) {
            insurance = metadata;
            console.log("✅ Extracted insurance (old format):", insurance);
          } else if (metadata.visits && Array.isArray(metadata.visits)) {
            visits = metadata.visits;
            console.log("✅ Extracted visits (old format):", visits.length);
          }
        }
      }
    });
  } else {
    console.log("⚠️ PatientInformation: No thinking messages provided");
  }
  
  // Extract from event data (patient_summary, visits, eligibility) - fallback if not in thinking messages
  if (eventData) {
    // Extract demographics from patient_summary if not found in thinking messages
    if (!demographics && eventData.patient_summary) {
      const ps = eventData.patient_summary;
      if (ps.name || ps.dob) {
        // Parse name if it's a string like "First Last"
        const nameParts = ps.name ? ps.name.split(' ') : [];
        demographics = {
          first_name: nameParts[0] || null,
          last_name: nameParts.slice(1).join(' ') || null,
          date_of_birth: ps.dob,
          member_id: ps.member_id
        };
      }
    }
    
    // Extract insurance from patient_summary if not found in thinking messages
    if (!insurance && eventData.patient_summary) {
      const ps = eventData.patient_summary;
      if (ps.insurance || ps.member_id) {
        insurance = {
          payer_name: ps.insurance,
          member_id: ps.member_id
        };
      }
    }
    
    // Extract visits from event data if not found in thinking messages
    if (visits.length === 0 && eventData.visits && Array.isArray(eventData.visits)) {
      visits = eventData.visits;
    }
    
    // Check for eligibility data (from eligibility_check event)
    if (eventData.eligibility_status || eventData.status || 
        (eventData.coverage_start && eventData.coverage_end) ||
        eventData.product_type) {
      eligibility = {
        status: eventData.eligibility_status || eventData.status,
        coverage_start: eventData.coverage_start,
        coverage_end: eventData.coverage_end,
        product_type: eventData.product_type,
        plan_name: eventData.plan_name,
        member_id: eventData.member_id,
        payer_name: eventData.payer_name,
        summary: eventData.summary,
        cached: eventData.cached
      };
    }
  }
  
  // Build summary text
  const summaryParts: string[] = [];
  if (demographics) {
    const name = [demographics.first_name, demographics.last_name].filter(Boolean).join(' ') || 'Patient';
    summaryParts.push(name);
    if (demographics.date_of_birth) summaryParts.push(`DOB: ${demographics.date_of_birth}`);
    if (demographics.member_id) summaryParts.push(`Member ID: ${demographics.member_id}`);
  }
  if (insurance) {
    if (insurance.payer_name) summaryParts.push(`Insurance: ${insurance.payer_name}`);
    if (insurance.plan_name && !summaryParts.some(p => p.includes(insurance.plan_name))) {
      summaryParts.push(`Plan: ${insurance.plan_name}`);
    }
  }
  if (visits.length > 0) {
    summaryParts.push(`${visits.length} visit(s)`);
  }
  
  const summaryText = summaryParts.length > 0 ? summaryParts.join(' • ') : 'Loading patient information...';
  const hasEmr = demographics || insurance;
  const hasVisits = visits.length > 0;
  const hasEligibility = eligibility;
  
  return (
    <div className="mt-2 pl-2 border-l-2 border-blue-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown size={12} className="text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight size={12} className="text-gray-400 flex-shrink-0" />
        )}
        <span className="font-medium text-gray-700 text-xs">Patient Information</span>
      </button>
      <div className="text-xs text-gray-600 mt-1 ml-4">{summaryText}</div>
      
      {isExpanded && (
        <div className="mt-2 ml-4 space-y-2 pb-2">
          {/* EMR Sub-section */}
          <div className="pl-2 border-l-2 border-gray-200">
              <button
                onClick={() => setEmrExpanded(!emrExpanded)}
                className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
              >
                {emrExpanded ? (
                  <ChevronDown size={10} className="text-gray-400 flex-shrink-0" />
                ) : (
                  <ChevronRight size={10} className="text-gray-400 flex-shrink-0" />
                )}
                <span className="font-medium text-gray-700 text-xs">EMR</span>
                {hasEmr && (
                  <span className="text-xs text-gray-500 ml-auto flex-shrink-0">({demographics && insurance ? '2' : '1'} items)</span>
                )}
              </button>
              
              {emrExpanded && (
                <div className="ml-4 mt-1 space-y-2 pb-1">
                  {/* Demographics Details */}
                  {demographics ? (
                    <div className="space-y-0.5 text-xs text-gray-600">
                      <div className="font-medium text-gray-700 mb-1">Demographics</div>
                      {demographics.first_name && demographics.last_name && (
                        <div><span className="font-medium">Name:</span> {demographics.first_name} {demographics.last_name}</div>
                      )}
                      {demographics.date_of_birth && (
                        <div><span className="font-medium">DOB:</span> {demographics.date_of_birth}</div>
                      )}
                      {demographics.sex && (
                        <div><span className="font-medium">Sex:</span> {demographics.sex}</div>
                      )}
                      {demographics.member_id && (
                        <div><span className="font-medium">Member ID:</span> {demographics.member_id}</div>
                      )}
                      {/* Show any other demographic fields */}
                      {Object.entries(demographics).map(([key, value]) => {
                        if (!['first_name', 'last_name', 'date_of_birth', 'sex', 'member_id'].includes(key) && value) {
                          return (
                            <div key={key} className="text-gray-500">
                              <span className="font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span> {String(value)}
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500 italic">No demographics data loaded</div>
                  )}
                  
                  {/* Insurance Details */}
                  {insurance ? (
                    <div className="space-y-0.5 text-xs text-gray-600 mt-2">
                      <div className="font-medium text-gray-700 mb-1">Insurance</div>
                      {insurance.payer_name && (
                        <div><span className="font-medium">Payer:</span> {insurance.payer_name}</div>
                      )}
                      {insurance.payer_id && (
                        <div><span className="font-medium">Payer ID:</span> {insurance.payer_id}</div>
                      )}
                      {insurance.plan_name && (
                        <div><span className="font-medium">Plan Name:</span> {insurance.plan_name}</div>
                      )}
                      {insurance.member_id && (
                        <div><span className="font-medium">Member ID:</span> {insurance.member_id}</div>
                      )}
                      {/* Show any other insurance fields */}
                      {Object.entries(insurance).map(([key, value]) => {
                        if (!['payer_name', 'payer_id', 'plan_name', 'member_id'].includes(key) && value) {
                          return (
                            <div key={key} className="text-gray-500">
                              <span className="font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span> {String(value)}
                            </div>
                          );
                        }
                        return null;
                      })}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500 italic mt-2">No insurance data loaded</div>
                  )}
                </div>
              )}
            </div>
          
          {/* Visit Summaries Sub-section */}
          <div className="pl-2 border-l-2 border-gray-200">
            <button
              onClick={() => setVisitsExpanded(!visitsExpanded)}
              className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
            >
              {visitsExpanded ? (
                <ChevronDown size={10} className="text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronRight size={10} className="text-gray-400 flex-shrink-0" />
              )}
              <span className="font-medium text-gray-700 text-xs">Visit Summaries</span>
              {hasVisits && (
                <span className="text-xs text-gray-500 ml-auto flex-shrink-0">({visits.length})</span>
              )}
            </button>
            
            {visitsExpanded && (
              <div className="ml-4 mt-1 space-y-2 pb-1 text-xs">
                {hasVisits ? (
                  <>
                    {[...visits]
                      .sort((a: any, b: any) => {
                        // Sort from latest (future) to oldest
                        const dateA = a.visit_date ? new Date(a.visit_date).getTime() : 0;
                        const dateB = b.visit_date ? new Date(b.visit_date).getTime() : 0;
                        return dateB - dateA; // Descending order (newest first)
                      })
                      .slice(0, 10)
                      .map((visit: any, idx: number) => {
                      let visitDateStr = '';
                      if (visit.visit_date) {
                        try {
                          visitDateStr = new Date(visit.visit_date).toLocaleDateString();
                        } catch (e) {
                          visitDateStr = visit.visit_date;
                        }
                      }
                      
                      return (
                        <div key={idx} className="text-gray-600 bg-gray-50 p-1.5 rounded">
                          {visitDateStr && (
                            <div className="font-medium">
                              {visitDateStr}
                              {visit.status && (
                                <span className={`ml-2 px-1 py-0.5 rounded text-xs ${
                                  visit.status === 'scheduled' ? 'bg-blue-100 text-blue-700' :
                                  visit.status === 'completed' ? 'bg-green-100 text-green-700' :
                                  'bg-gray-100 text-gray-600'
                                }`}>
                                  {visit.status}
                                </span>
                              )}
                              {visit.event_tense && (
                                <span className={`ml-2 px-1 py-0.5 rounded text-xs ${
                                  visit.event_tense === 'PAST' ? 'bg-gray-200 text-gray-700' : 'bg-blue-100 text-blue-700'
                                }`}>
                                  {visit.event_tense}
                                </span>
                              )}
                            </div>
                          )}
                          {visit.visit_type && (
                            <div className="text-gray-600 mt-0.5">{visit.visit_type}</div>
                          )}
                          {visit.eligibility_status && (
                            <div className="mt-0.5">
                              <span className={`text-xs font-medium ${
                                visit.eligibility_status === 'YES' ? 'text-green-600' : 
                                visit.eligibility_status === 'NO' ? 'text-red-600' : 
                                'text-gray-600'
                              }`}>
                                {visit.eligibility_status === 'YES' ? '✅ Eligible' : 
                                 visit.eligibility_status === 'NO' ? '❌ Not Eligible' : 
                                 '⏳ Unknown'}
                              </span>
                              {visit.eligibility_probability !== undefined && visit.eligibility_probability !== null && (
                                <span className="ml-2 text-gray-600">
                                  ({Math.round(visit.eligibility_probability * 100)}% probability)
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {visits.length > 10 && (
                      <div className="text-gray-500 italic">...and {visits.length - 10} more visit(s)</div>
                    )}
                  </>
                ) : (
                  <div className="text-gray-500 italic">No visit data loaded</div>
                )}
              </div>
            )}
          </div>
          
          {/* Eligibility Sub-section */}
          <div className="pl-2 border-l-2 border-gray-200">
            <button
              onClick={() => setEligibilityExpanded(!eligibilityExpanded)}
              className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
            >
              {eligibilityExpanded ? (
                <ChevronDown size={10} className="text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronRight size={10} className="text-gray-400 flex-shrink-0" />
              )}
              <span className="font-medium text-gray-700 text-xs">Eligibility</span>
              {hasEligibility && (
                <span className="text-xs text-gray-500 ml-auto flex-shrink-0">Available</span>
              )}
            </button>
            
            {eligibilityExpanded && (
              <div className="ml-4 mt-1 space-y-1 pb-1 text-xs text-gray-600">
                {hasEligibility ? (
                  <>
                    {eligibility.status && (
                      <div>
                        <span className="font-medium">Status:</span> {eligibility.status === "YES" ? "✅ Eligible" : eligibility.status === "NO" ? "❌ Not Eligible" : eligibility.status}
                      </div>
                    )}
                    {eligibility.coverage_start && eligibility.coverage_end && (
                      <div>
                        <span className="font-medium">Coverage Period:</span> {eligibility.coverage_start} to {eligibility.coverage_end}
                      </div>
                    )}
                    {eligibility.product_type && (
                      <div>
                        <span className="font-medium">Product Type:</span> {eligibility.product_type}
                      </div>
                    )}
                    {eligibility.plan_name && (
                      <div>
                        <span className="font-medium">Plan Name:</span> {eligibility.plan_name}
                      </div>
                    )}
                    {eligibility.member_id && (
                      <div>
                        <span className="font-medium">Member ID:</span> {eligibility.member_id}
                      </div>
                    )}
                    {eligibility.payer_name && (
                      <div>
                        <span className="font-medium">Payer:</span> {eligibility.payer_name}
                      </div>
                    )}
                    {eligibility.summary && (
                      <div className="mt-1 italic text-gray-500">{eligibility.summary}</div>
                    )}
                    {eligibility.cached && (
                      <div className="text-xs text-gray-400">(Using cached result)</div>
                    )}
                  </>
                ) : (
                  <div className="text-gray-500 italic">No eligibility check performed yet</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Helper component for What We Found with sub-sections
function WhatWeFound({ events }: { events: ProcessEvent[] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [interpretationExpanded, setInterpretationExpanded] = useState(false);
  const [scoringExpanded, setScoringExpanded] = useState(false);
  const [planningExpanded, setPlanningExpanded] = useState(false);
  
  // Extract events by phase
  const interpretationEvent = events.find((e) => e.phase === "interpretation");
  const scoringEvent = events.find((e) => e.phase === "scoring");
  const planningEvent = events.find((e) => e.phase === "planning");
  
  // Build summary text
  const summaryParts: string[] = [];
  if (interpretationEvent?.message) {
    const missingFieldsMatch = interpretationEvent.message.match(/Missing fields: (.+)/);
    if (missingFieldsMatch) {
      const fields = missingFieldsMatch[1].split(", ").map((f) => f.replace(/health_plan\.|timing\./g, ""));
      summaryParts.push(`Missing: ${fields.join(", ")}`);
    }
  }
  if (scoringEvent?.data?.score_summary) {
    const prob = scoringEvent.data.score_summary.probability;
    if (prob !== undefined) {
      summaryParts.push(`${(prob * 100).toFixed(0)}% probability`);
    }
  }
  if (planningEvent?.data) {
    if (planningEvent.data.questions_count) {
      summaryParts.push(`${planningEvent.data.questions_count} question(s)`);
    }
    if (planningEvent.data.improvement_plan_count) {
      summaryParts.push(`${planningEvent.data.improvement_plan_count} action(s)`);
    }
  }
  
  const summaryText = summaryParts.length > 0 ? summaryParts.join(" • ") : "Analysis complete";
  
  return (
    <div className="mt-2 pl-2 border-l-2 border-blue-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown size={12} className="text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight size={12} className="text-gray-400 flex-shrink-0" />
        )}
        <span className="font-medium text-gray-700 text-xs">What We Found</span>
      </button>
      <div className="text-xs text-gray-600 mt-1 ml-4">{summaryText}</div>
      
      {isExpanded && (
        <div className="mt-2 ml-4 space-y-2 pb-2">
          {/* Interpretation Sub-section */}
          <div className="pl-2 border-l-2 border-gray-200">
            <button
              onClick={() => setInterpretationExpanded(!interpretationExpanded)}
              className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
            >
              {interpretationExpanded ? (
                <ChevronDown size={10} className="text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronRight size={10} className="text-gray-400 flex-shrink-0" />
              )}
              <span className="font-medium text-gray-700 text-xs">Interpretation</span>
              {interpretationEvent && (
                <span className="text-xs text-gray-500 ml-auto flex-shrink-0">Complete</span>
              )}
            </button>
            
            {interpretationExpanded && (
              <div className="ml-4 mt-1 space-y-1 pb-1 text-xs text-gray-600">
                {interpretationEvent ? (
                  <>
                    {interpretationEvent.message && (
                      <div className="mb-2">
                        {interpretationEvent.message
                          .replace(/^Interpretation complete.*? - /, "")
                          .replace(/^Interpretation complete.*/, "")
                          .trim() || "Interpretation complete"}
                      </div>
                    )}
                    {interpretationEvent.thinking_messages && interpretationEvent.thinking_messages.length > 0 && (
                      <div className="space-y-1">
                        {interpretationEvent.thinking_messages.map((thinking, idx) => (
                          <div key={idx} className="text-gray-500 pl-2 border-l-2 border-blue-200">
                            <div className="font-medium text-gray-600 mb-0.5">{thinking.message}</div>
                            {thinking.metadata && typeof thinking.metadata === 'object' && (
                              <div className="mt-1 text-gray-500">
                                <pre className="bg-gray-50 p-1 rounded overflow-x-auto text-xs">
                                  {JSON.stringify(thinking.metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-gray-500 italic">No interpretation data</div>
                )}
              </div>
            )}
          </div>
          
          {/* Scoring Sub-section */}
          <div className="pl-2 border-l-2 border-gray-200">
            <button
              onClick={() => setScoringExpanded(!scoringExpanded)}
              className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
            >
              {scoringExpanded ? (
                <ChevronDown size={10} className="text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronRight size={10} className="text-gray-400 flex-shrink-0" />
              )}
              <span className="font-medium text-gray-700 text-xs">Scoring</span>
              {scoringEvent?.data?.score_summary && (
                <span className="text-xs text-gray-500 ml-auto flex-shrink-0">
                  {scoringEvent.data.score_summary.probability !== undefined 
                    ? `${(scoringEvent.data.score_summary.probability * 100).toFixed(0)}%`
                    : "Complete"}
                </span>
              )}
            </button>
            
            {scoringExpanded && (
              <div className="ml-4 mt-1 space-y-1 pb-1 text-xs text-gray-600">
                {scoringEvent?.data?.score_summary ? (
                  <>
                    {scoringEvent.data.score_summary.probability !== undefined && (
                      <div>
                        <span className="font-medium">Probability:</span> {(scoringEvent.data.score_summary.probability * 100).toFixed(1)}%
                      </div>
                    )}
                    {scoringEvent.data.score_summary.confidence !== undefined && (
                      <div>
                        <span className="font-medium">Confidence:</span> {(scoringEvent.data.score_summary.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                    {scoringEvent.data.score_summary.sample_size && (
                      <div>
                        <span className="font-medium">Sample Size:</span> {scoringEvent.data.score_summary.sample_size} transactions
                      </div>
                    )}
                    {scoringEvent.data.score_summary.confidence_interval && (
                      <div>
                        <span className="font-medium">Confidence Interval:</span> {Math.round(scoringEvent.data.score_summary.confidence_interval.lower_bound * 100)}% - {Math.round(scoringEvent.data.score_summary.confidence_interval.upper_bound * 100)}%
                      </div>
                    )}
                    {scoringEvent.data.score_summary.volatility && (
                      <div className="mt-2">
                        <div className="font-medium text-gray-700 mb-1">Volatility Metrics</div>
                        <div className="pl-2 space-y-0.5 text-gray-500">
                          {scoringEvent.data.score_summary.volatility.volatility_score !== undefined && (
                            <div>Volatility Score: {(scoringEvent.data.score_summary.volatility.volatility_score * 100).toFixed(1)}%</div>
                          )}
                          {scoringEvent.data.score_summary.volatility.coefficient_of_variation !== undefined && (
                            <div>Coefficient of Variation: {scoringEvent.data.score_summary.volatility.coefficient_of_variation.toFixed(3)}</div>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-gray-500 italic">No scoring data</div>
                )}
              </div>
            )}
          </div>
          
          {/* Planning Sub-section */}
          <div className="pl-2 border-l-2 border-gray-200">
            <button
              onClick={() => setPlanningExpanded(!planningExpanded)}
              className="w-full text-left flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-1 -mx-1 transition-colors"
            >
              {planningExpanded ? (
                <ChevronDown size={10} className="text-gray-400 flex-shrink-0" />
              ) : (
                <ChevronRight size={10} className="text-gray-400 flex-shrink-0" />
              )}
              <span className="font-medium text-gray-700 text-xs">Planning</span>
              {planningEvent?.data && (
                <span className="text-xs text-gray-500 ml-auto flex-shrink-0">
                  {planningEvent.data.questions_count || 0} question(s), {planningEvent.data.improvement_plan_count || 0} action(s)
                </span>
              )}
            </button>
            
            {planningExpanded && (
              <div className="ml-4 mt-1 space-y-1 pb-1 text-xs text-gray-600">
                {planningEvent ? (
                  <>
                    {planningEvent.message && (
                      <div className="mb-2">
                        {planningEvent.message
                          .replace(/^Planning complete.*?\n/, "")
                          .replace(/^Planning complete.*/, "")
                          .trim() || "Planning complete"}
                      </div>
                    )}
                    {planningEvent.data?.questions_count !== undefined && (
                      <div>
                        <span className="font-medium">Questions Generated:</span> {planningEvent.data.questions_count}
                      </div>
                    )}
                    {planningEvent.data?.improvement_plan_count !== undefined && (
                      <div>
                        <span className="font-medium">Improvement Actions:</span> {planningEvent.data.improvement_plan_count}
                      </div>
                    )}
                    {planningEvent.thinking_messages && planningEvent.thinking_messages.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <div className="font-medium text-gray-700 mb-1">Planning Details</div>
                        {planningEvent.thinking_messages.map((thinking, idx) => (
                          <div key={idx} className="text-gray-500 pl-2 border-l-2 border-blue-200">
                            <div className="font-medium text-gray-600 mb-0.5">{thinking.message}</div>
                            {thinking.metadata && typeof thinking.metadata === 'object' && (
                              <div className="mt-1 text-gray-500">
                                <pre className="bg-gray-50 p-1 rounded overflow-x-auto text-xs">
                                  {JSON.stringify(thinking.metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-gray-500 italic">No planning data</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function EligibilityProcessView({
  events,
  isExpanded,
  onToggle,
  isStreaming = false,
}: EligibilityProcessViewProps) {
  // Sort events by timestamp
  const sortedEvents = [...events].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const phaseOrder: ProcessEvent["phase"][] = [
    "patient_loading",
    "eligibility_check",
    "interpretation",
    "scoring",
    "planning",
    "conversation",
  ];

  return (
    <div className="flex gap-3 relative">
      {/* Timeline line and icon */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div className={`w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center border-2 border-white shadow-sm ${isStreaming ? 'animate-pulse' : ''}`}>
          <Brain size={12} />
        </div>
        {isExpanded && (
          <div className="w-0.5 h-full bg-blue-200 mt-1 min-h-[20px]"></div>
        )}
      </div>

      {/* Content area */}
      <div className="flex-1 min-w-0">
        <button
          onClick={onToggle}
          className="w-full text-left flex items-center justify-between gap-2 py-1.5 group"
        >
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-0.5 h-4 bg-blue-500 flex-shrink-0"></div>
            <span className="text-xs text-blue-600 font-medium truncate">
              {isStreaming ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></span>
                  <span>Processing Eligibility Check</span>
                  <span className="inline-block">
                    <span className="animate-dots-1">.</span>
                    <span className="animate-dots-2">.</span>
                    <span className="animate-dots-3">.</span>
                  </span>
                </span>
              ) : (
                `Eligibility Check`
              )}
            </span>
          </div>
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronUp size={12} className="text-blue-400 group-hover:text-blue-600 transition-colors" />
            ) : (
              <ChevronDown size={12} className="text-blue-400 group-hover:text-blue-600 transition-colors" />
            )}
          </div>
        </button>

        {isExpanded && (
          <div className="ml-2.5 mt-1 pb-2">
            <div className="max-h-[400px] overflow-y-auto space-y-2 custom-scrollbar pr-1">
              {(() => {
                // Filter to only completed/error events (or in_progress if streaming)
                const filteredEvents = sortedEvents.filter(
                  (event) => event.status === "complete" || event.status === "error" || (event.status === "in_progress" && isStreaming)
                );
                
                // Deduplicate by phase - keep only the latest event for each phase
                const phaseMap = new Map<string, typeof filteredEvents[0]>();
                filteredEvents.forEach((event) => {
                  const existing = phaseMap.get(event.phase);
                  if (!existing || new Date(event.timestamp) > new Date(existing.timestamp)) {
                    phaseMap.set(event.phase, event);
                  }
                });
                
                // Group interpretation/scoring/planning into "Analysis"
                const groupedEvents: Array<{ phase: string; label: string; events: typeof filteredEvents; isError: boolean }> = [];
                
                // Patient Information (patient_loading)
                const patientEvent = phaseMap.get("patient_loading");
                if (patientEvent) {
                  groupedEvents.push({
                    phase: "patient_loading",
                    label: "Patient Information",
                    events: [patientEvent],
                    isError: patientEvent.status === "error"
                  });
                }
                
                // Analysis (interpretation + scoring + planning combined)
                const analysisEvents = ["interpretation", "scoring", "planning"]
                  .map((phase) => phaseMap.get(phase))
                  .filter((e): e is typeof filteredEvents[0] => e !== undefined);
                
                if (analysisEvents.length > 0) {
                  groupedEvents.push({
                    phase: "analysis",
                    label: "What We Found",
                    events: analysisEvents,
                    isError: analysisEvents.some((e) => e.status === "error")
                  });
                }
                
                // Eligibility Check is merged into Patient Information, so we don't create a separate group
                
                // Response (conversation)
                const responseEvent = phaseMap.get("conversation");
                if (responseEvent) {
                  groupedEvents.push({
                    phase: "conversation",
                    label: "Response",
                    events: [responseEvent],
                    isError: responseEvent.status === "error"
                  });
                }
                
                return groupedEvents.map((group, idx) => {
                  const Icon = phaseIcons[group.events[0].phase] || Brain;
                  
                  return (
                    <div key={idx} className="text-xs">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon 
                          size={14} 
                          className={
                            group.isError ? "text-red-500" :
                            "text-gray-600"
                          }
                        />
                        <span className="font-medium text-gray-700">{group.label}</span>
                        {group.isError && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                            Error
                          </span>
                        )}
                      </div>
                      
                      {/* Patient Information - only for patient_loading */}
                      {group.events[0].phase === "patient_loading" && (
                        <div className="ml-6 mt-2 space-y-1.5">
                          {(() => {
                            // Find eligibility_check event data to pass to PatientInformation
                            const eligibilityEvent = phaseMap.get("eligibility_check");
                            const eligibilityData = eligibilityEvent?.data || null;
                            
                            // Merge patient_loading data with eligibility_check data
                            const mergedEventData = {
                              ...(group.events[0].data || {}),
                              // Merge eligibility data if available (use same keys as eligibility_check emits)
                              ...(eligibilityData && {
                                status: eligibilityData.status,
                                coverage_start: eligibilityData.coverage_start,
                                coverage_end: eligibilityData.coverage_end,
                                product_type: eligibilityData.product_type,
                                plan_name: eligibilityData.plan_name,
                                member_id: eligibilityData.member_id,
                                payer_name: eligibilityData.payer_name,
                                summary: eligibilityData.summary,
                                cached: eligibilityData.cached
                              })
                            };
                            
                            return (
                              <PatientInformation 
                                thinkingMessages={group.events[0].thinking_messages} 
                                eventData={mergedEventData}
                              />
                            );
                          })()}
                        </div>
                      )}
                      
                      {/* What We Found - for analysis group */}
                      {group.label === "What We Found" && (
                        <div className="ml-6 mt-2 space-y-1.5">
                          <WhatWeFound events={group.events} />
                        </div>
                      )}
                      
                      {/* Event data - show only for Response group (What We Found and Patient Information are handled by components) */}
                      {group.label === "Response" && group.events.map((event, eventIdx) => (
                        <div key={eventIdx}>
                          {event.data && (event.status === "complete" || event.status === "error") && (
                      <div className="mt-1 space-y-1 text-gray-500 ml-6">
                        {/* Conversation summary */}
                        {event.data.conversation_summary && (
                          <div className="pl-2 border-l-2 border-gray-200">
                            <div className="font-medium text-gray-600 mb-0.5">Response:</div>
                            <div className="text-xs">{event.data.conversation_summary}</div>
                          </div>
                        )}
                      </div>
                        )}
                        </div>
                      ))}
                      
                      {/* Show scoring/planning data only if not in What We Found */}
                      {group.label !== "What We Found" && group.label !== "Patient Information" && group.label !== "Response" && group.events.map((event, eventIdx) => (
                        <div key={eventIdx}>
                          {event.data && (event.status === "complete" || event.status === "error") && (
                      <div className="mt-1 space-y-1 text-gray-500 ml-6">
                        {/* Score summary - only for scoring events */}
                        {event.phase === "scoring" && event.data.score_summary && (
                          <div className="pl-2 border-l-2 border-gray-200">
                            <div className="font-medium text-gray-600 mb-0.5">Scoring Results:</div>
                            {event.data.score_summary.probability !== undefined && (
                              <div>Probability: {(event.data.score_summary.probability * 100).toFixed(1)}%</div>
                            )}
                            {event.data.score_summary.confidence !== undefined && (
                              <div>Confidence: {(event.data.score_summary.confidence * 100).toFixed(0)}%</div>
                            )}
                            {event.data.score_summary.sample_size && (
                              <div>Sample Size: {event.data.score_summary.sample_size} transactions</div>
                            )}
                            {event.data.score_summary.confidence_interval && (
                              <div>
                                CI: {Math.round(event.data.score_summary.confidence_interval.lower_bound * 100)}% - {Math.round(event.data.score_summary.confidence_interval.upper_bound * 100)}%
                              </div>
                            )}
                          </div>
                        )}

                        {/* Questions and plan counts */}
                        {event.data.questions_count !== undefined && (
                          <div className="text-xs text-gray-500">
                            Generated {event.data.questions_count} question(s)
                          </div>
                        )}
                        {event.data.improvement_plan_count !== undefined && (
                          <div className="text-xs text-gray-500">
                            Created {event.data.improvement_plan_count} improvement action(s)
                          </div>
                        )}
                          </div>
                        )}
                        </div>
                      ))}
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
