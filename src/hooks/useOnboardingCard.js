import { useState, useCallback } from 'react';

export function useOnboardingCard(cardId) {
  const key = `sp_onboard_${cardId}`;
  const [visible, setVisible] = useState(() => localStorage.getItem(key) !== '1');

  const dismiss = useCallback(() => {
    localStorage.setItem(key, '1');
    setVisible(false);
  }, [key]);

  return { visible, dismiss };
}
