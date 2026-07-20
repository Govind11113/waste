import { useTheme } from '../context/ThemeContext';

// Simple toggle button that flips the dark mode state.
// It shows a sun icon when dark mode is active (click to go light) and a moon icon otherwise.
export default function DarkModeToggle() {
  const { darkMode, toggleDarkMode } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleDarkMode}
      className="p-2 rounded-full bg-surface-container-low hover:bg-surface-container-high transition-colors"
      title="Toggle dark mode"
    >
      <span className="material-symbols-outlined text-xl">
        {darkMode ? 'light_mode' : 'dark_mode'}
      </span>
    </button>
  );
}
