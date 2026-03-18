import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';

describe('NewRunProvider', () => {
  it('test_handles_null_prompt_text', () => {
    const { result } = renderHook(() => {
      const [promptText, setPromptText] = React.useState<string | null>(null);
      
      const openNewRun = React.useCallback(() => {
        setPromptText((current) => {
          if (!current) return current;
          return current.includes('LEGACY')
            ? current.replace('LEGACY', '').trim()
            : current;
        });
      }, []);

      return { promptText, openNewRun };
    });

    expect(result.current.promptText).toBe(null);
    
    act(() => {
      result.current.openNewRun();
    });

    expect(result.current.promptText).toBe(null);
  });
});
