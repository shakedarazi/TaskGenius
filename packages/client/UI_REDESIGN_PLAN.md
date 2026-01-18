# UI Redesign Plan - TaskGenius Frontend

## Overview
Redesign the UI with a modern navy/light-blue theme using Bootstrap 5, while preserving ALL existing business logic.

## Files to be Edited/Created

### New Files:
1. `src/styles/theme.css` - Global theme variables (navy/light-blue)
2. `src/styles/tasks.css` - Task-specific styles (table/cards, priority badges)

### Modified Files:
1. `package.json` - Add Bootstrap 5 and bootstrap-icons
2. `src/main.tsx` - Import Bootstrap CSS and theme
3. `src/index.css` - Update with new theme variables, keep existing structure
4. `src/components/TaskList.tsx` - Add Bootstrap classes, responsive table/cards
5. `src/pages/TasksPage.tsx` - Add Bootstrap classes for header/filters
6. `src/components/TaskForm.tsx` - Add Bootstrap form classes
7. `src/components/TaskEditForm.tsx` - Add Bootstrap form classes
8. `src/components/Layout.tsx` - Add Bootstrap classes for header/nav
9. `index.html` - Add RTL support detection

## Bootstrap Integration Approach

1. **Installation**: Add to `package.json`:
   - `bootstrap@^5.3.0`
   - `bootstrap-icons@^1.11.0` (optional, for icons)

2. **Import Location**: 
   - Import Bootstrap CSS in `src/main.tsx` before `index.css`
   - Import theme overrides after Bootstrap
   - Use Bootstrap JS via CDN in `index.html` (or import if needed)

3. **Customization**:
   - Override Bootstrap variables in `src/styles/theme.css`
   - Use CSS custom properties for theme colors
   - Maintain existing class names where possible for backward compatibility

## Theme Variables/Tokens

### Colors (Navy/Light-Blue Theme):
```css
--theme-navy-primary: #1a365d;      /* Deep navy */
--theme-navy-dark: #0f2027;         /* Darker navy */
--theme-light-blue: #4a90e2;         /* Light blue accent */
--theme-light-blue-light: #6ba3e8;  /* Lighter blue */
--theme-background: #f0f4f8;        /* Light blue-gray background */
--theme-surface: #ffffff;            /* White surface */
--theme-text: #1a202c;              /* Dark text */
--theme-text-secondary: #718096;    /* Gray text */
--theme-error: #e53e3e;              /* Red for errors */
--theme-success: #38a169;            /* Green for success */
```

### Priority Colors (Red gradient for urgency):
```css
--priority-low: #48bb78;            /* Green */
--priority-medium: #ed8936;          /* Orange */
--priority-high: #f56565;           /* Red */
--priority-urgent: #c53030;          /* Dark red */
```

### Spacing, Radius, Shadows:
- Keep existing spacing scale
- Use Bootstrap's spacing utilities
- Rounded corners: `--radius-md: 8px`, `--radius-lg: 12px`
- Soft shadows for elevation

## RTL/LTR Handling

1. **Detection**: Check if content contains Hebrew characters
2. **Implementation**: 
   - Add `dir="rtl"` or `dir="ltr"` to `<html>` or container elements
   - Use Bootstrap's RTL utilities where needed
   - Test with Hebrew task titles/descriptions
3. **Typography**: Ensure proper font rendering for both languages

## Mobile Layout Strategy

### Desktop (md+ screens, ≥768px):
- Use Bootstrap table (`<table class="table">`) for tasks
- Show all columns: Title, Priority, Deadline, Status, Actions
- Left border color based on priority
- Priority badge in priority column

### Mobile (< 768px):
- Switch to Bootstrap cards (`<div class="card">`)
- Stack tasks vertically
- Each card shows: Title, Priority badge, Deadline, Actions
- Priority indicated by left border + badge
- Responsive breakpoint: Bootstrap's `md` (768px)

### Implementation:
- Use CSS media queries with Bootstrap classes
- Conditional rendering: `className` based on screen size OR CSS-only approach
- Prefer CSS-only (display: table vs display: block) for performance

## Component-Specific Changes

### TaskList.tsx:
- Wrap in Bootstrap container
- Desktop: `<table class="table table-hover">` with Bootstrap classes
- Mobile: `<div class="row">` with cards
- Priority badge: `<span class="badge bg-{priority}">`
- Left border: `border-start border-{priority}-{width}`

### TasksPage.tsx:
- Header: Bootstrap navbar or card header
- Filters: Bootstrap form controls (`form-select`, `form-control`)
- Buttons: Bootstrap button classes (`btn btn-primary`)

### Forms (TaskForm, TaskEditForm):
- Use Bootstrap form classes (`form-control`, `form-select`, `form-label`)
- Button groups with Bootstrap classes
- Maintain existing form logic

### Layout.tsx:
- Bootstrap navbar for header
- Bootstrap footer classes
- Responsive navigation

## Animations/Transitions

1. **Subtle animations**:
   - Button hover: `transition: all 0.2s ease`
   - Card hover: slight elevation change
   - List updates: fade-in for new items
   - No disruptive motion

2. **Implementation**:
   - CSS transitions (no JS libraries unless already present)
   - Use Bootstrap's built-in transitions
   - Optional: framer-motion only if low-risk addition

## Accessibility

1. **Contrast**: Ensure WCAG AA compliance (4.5:1 for text)
2. **Focus states**: Visible focus rings on interactive elements
3. **Touch targets**: Minimum 44x44px on mobile
4. **ARIA labels**: Maintain existing, add where needed

## Verification Checklist

- [ ] `npm install` runs successfully
- [ ] `npm run lint` passes (if present)
- [ ] `npm run build` succeeds
- [ ] `npm run dev` starts without errors
- [ ] Desktop: Tasks display in table format
- [ ] Mobile: Tasks display as cards
- [ ] Priority colors visible and correct
- [ ] RTL works with Hebrew content
- [ ] Forms styled with Bootstrap
- [ ] Buttons have hover states
- [ ] No console errors
- [ ] All existing functionality preserved
