export interface PromptSection {
    key: string;
    type: 'string' | 'object' | 'array';
    value: any;
    order: number;
    description?: string;
}

// Known section descriptions for better UX
const SECTION_DESCRIPTIONS: Record<string, string> = {
    'ROLE': 'Defines the AI assistant\'s role and persona',
    'CONTEXT': 'Provides contextual information for the prompt',
    'MOBIUSOS_CONTEXT': 'Mobius OS system context and capabilities',
    'STRATEGY_CONTEXT': 'Strategy-specific guidance and approach',
    'STAGE_GUIDANCE': 'Guidance for different conversation stages',
    'ANALYSIS': 'Instructions for analyzing user queries',
    'OUTPUT': 'Output format, schema, and constraints',
    'RAG_INFO': 'RAG (Retrieval Augmented Generation) information handling',
    'CONSTRAINTS': 'Behavioral constraints and rules',
    'GENERATION_CONFIG': 'LLM generation parameters (temperature, tokens, etc.)',
    'CONVERSATION_HISTORY': 'Conversation history handling configuration',
    'USER_PREFERENCES': 'User preference handling',
    'ORGANIZATION_CONTEXT': 'Organization-specific context'
};

// Preferred section order
const SECTION_ORDER = [
    'ROLE',
    'CONTEXT',
    'MOBIUSOS_CONTEXT',
    'STRATEGY_CONTEXT',
    'STAGE_GUIDANCE',
    'ANALYSIS',
    'OUTPUT',
    'RAG_INFO',
    'CONSTRAINTS',
    'GENERATION_CONFIG',
    'CONVERSATION_HISTORY',
    'USER_PREFERENCES',
    'ORGANIZATION_CONTEXT'
];

export function parsePromptConfig(config: any): PromptSection[] {
    if (!config || typeof config !== 'object') {
        return [];
    }

    const sections: PromptSection[] = [];

    // Preserve original key order from the input config
    const originalKeys = Object.keys(config);
    
    // Process keys in their original order
    originalKeys.forEach((key, originalIndex) => {
        const value = config[key];
        const type = getValueType(value);
        
        // Use original index as order to preserve order
        sections.push({
            key,
            type,
            value,
            order: originalIndex, // Preserve original order
            description: SECTION_DESCRIPTIONS[key] || `Custom section: ${key}`
        });
    });

    return sections;
}

function getValueType(value: any): 'string' | 'object' | 'array' {
    if (typeof value === 'string') {
        return 'string';
    }
    if (Array.isArray(value)) {
        return 'array';
    }
    if (value !== null && typeof value === 'object') {
        return 'object';
    }
    // Fallback for other types (number, boolean, null)
    return 'object';
}

export function reconstructPromptConfig(sections: PromptSection[]): any {
    const config: any = {};
    
    // Sort sections by order
    const sortedSections = [...sections].sort((a, b) => a.order - b.order);
    
    sortedSections.forEach(section => {
        config[section.key] = section.value;
    });
    
    return config;
}

