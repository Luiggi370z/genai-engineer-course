import { useCallback, useId, useState } from "react";

interface Disclosure {
  open: boolean;
  /** Spread onto the button that reveals the panel. */
  triggerProps: {
    type: "button";
    onClick: () => void;
    "aria-expanded": boolean;
    "aria-controls": string;
  };
  /** Spread onto the panel element, which the caller renders only when open. */
  panelProps: { id: string };
}

/**
 * Open/close state and the `aria-expanded` / `aria-controls` pair, in one place.
 *
 * A hook rather than a wrapper component because the two consumers disagree about
 * layout, not about behaviour: a deep dive's panel nests inside its trigger's
 * container, while a predict block's answer is a full-bleed footer that breaks out
 * of the padding the button sits in. A component would have to grow a prop for
 * each of those arrangements; the aria contract is the only part worth sharing.
 *
 * The chrome stays separate on purpose. A predict prompt must read as a task you
 * owe an answer to and a deep dive as an aside you may skip — if the two looked
 * alike, students would learn one habit for both, and the habit would be skipping.
 */
export function useDisclosure(): Disclosure {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  return {
    open,
    triggerProps: {
      type: "button",
      onClick: toggle,
      "aria-expanded": open,
      "aria-controls": panelId,
    },
    panelProps: { id: panelId },
  };
}
