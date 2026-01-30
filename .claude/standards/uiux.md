# UI/UX Standards

> Guidelines for user interface design and user experience patterns.

## Core Principles

1. **Clarity Over Cleverness** - Users should understand instantly
2. **Consistency** - Same patterns throughout the application
3. **Feedback** - Every action has a visible response
4. **Forgiveness** - Easy to undo, hard to make mistakes
5. **Efficiency** - Minimize steps to complete tasks

---

## Visual Design Foundations

### Typography

**Hierarchy:**
- H1: Primary page titles (one per page)
- H2: Section headers
- H3: Subsection headers
- Body: Primary content
- Caption: Supporting text, labels

**Best Practices:**
- Maximum 2-3 font families
- Maintain readable line lengths (45-75 characters)
- Adequate line height (1.4-1.6 for body text)
- Sufficient contrast against background

### Color

**Semantic Colors:**
| Purpose | Use Case |
|---------|----------|
| Primary | Main actions, brand identity |
| Secondary | Supporting actions |
| Success | Confirmations, completed states |
| Warning | Caution, needs attention |
| Error | Problems, destructive actions |
| Neutral | Backgrounds, borders, text |

**Accessibility:**
- Maintain 4.5:1 contrast ratio for text
- 3:1 for large text and UI components
- Don't convey meaning through color alone

### Spacing

**Consistent Scale:**
- Use a spacing scale (e.g., 4px base: 4, 8, 12, 16, 24, 32, 48, 64)
- Group related elements with less space
- Separate sections with more space
- Maintain consistent padding within components

---

## Component Standards

### Buttons

**Types:**
- Primary: Main action (one per section)
- Secondary: Alternative actions
- Tertiary/Ghost: Low-emphasis actions
- Destructive: Delete, remove actions

**States:**
- Default
- Hover
- Active/Pressed
- Focused
- Disabled
- Loading

**Guidelines:**
- Use action verbs ("Save", "Submit", "Create")
- Minimum touch target: 44x44px
- Clear visual distinction between types

### Forms

**Input Fields:**
- Clear labels (not just placeholders)
- Helpful placeholder text
- Visible required indicators
- Inline validation when possible

**Error Handling:**
- Show errors near the relevant field
- Use clear, helpful error messages
- Explain how to fix the problem
- Don't clear the form on error

**Best Practices:**
- One column layouts for most forms
- Group related fields
- Smart defaults where possible
- Minimize required fields

### Navigation

**Primary Navigation:**
- Consistent location
- Current page indication
- Accessible via keyboard
- Mobile-friendly (hamburger or tabs)

**Breadcrumbs:**
- Show hierarchy for deep structures
- Link all but current page
- Use ">" or "/" separators

### Feedback & Notifications

**Types:**
- Toast: Temporary, non-blocking messages
- Alert: In-page important information
- Modal: Requires user action
- Inline: Contextual feedback

**Guidelines:**
- Match urgency to importance
- Provide clear actions when needed
- Auto-dismiss for informational only
- Allow dismissal of non-critical alerts

---

## Interaction Patterns

### Loading States

**When to Show:**
- Any action taking >300ms
- Data fetching
- Form submissions

**How:**
- Skeleton screens for initial loads
- Spinners for actions
- Progress bars for long operations
- Disable buttons during submission

### Empty States

**Include:**
- Explanation of what would be here
- Illustration (optional)
- Clear call-to-action
- Help getting started

### Error States

**Components:**
- What went wrong (user-friendly)
- What they can do about it
- Way to get help if stuck
- Option to retry when applicable

---

## Responsive Design

### Breakpoints
| Name | Width | Target |
|------|-------|--------|
| Mobile | < 640px | Phones |
| Tablet | 640px - 1024px | Tablets |
| Desktop | > 1024px | Laptops/Desktops |

### Mobile-First Approach
- Design for mobile first
- Enhance for larger screens
- Touch-friendly targets (min 44px)
- Consider thumb zones

### Responsive Patterns
- Stack columns on mobile
- Hide secondary nav in hamburger
- Full-width buttons on mobile
- Simplify tables for small screens

---

## Motion & Animation

### Principles
- **Purpose:** Animation should have meaning
- **Speed:** Fast enough not to delay (150-300ms typical)
- **Easing:** Natural acceleration/deceleration
- **Respect preferences:** Honor `prefers-reduced-motion`

### Use Cases
- State transitions
- Loading indicators
- Micro-interactions (hover, click)
- Page transitions
- Drawing attention

---

## Writing for UI

### Voice & Tone
- Clear and concise
- Friendly but professional
- Action-oriented
- Consistent terminology

### Microcopy Guidelines
- Button labels: Action verbs
- Error messages: Helpful, not blaming
- Empty states: Encouraging
- Confirmations: Reassuring

### Examples
| Instead of | Use |
|------------|-----|
| "Invalid input" | "Please enter a valid email" |
| "Error occurred" | "Couldn't save. Please try again." |
| "Submit" | "Create Account" |
| "N/A" | "Not specified" |

---

## Checklists

### Design Review
- [ ] Follows established patterns
- [ ] Consistent with design system
- [ ] Accessible (contrast, labels, keyboard)
- [ ] Responsive across breakpoints
- [ ] Clear calls to action
- [ ] Appropriate feedback for actions
- [ ] Error states handled
- [ ] Loading states handled
- [ ] Empty states designed

### Before Handoff to Development
- [ ] All states documented
- [ ] Interactions specified
- [ ] Responsive behavior defined
- [ ] Assets exported correctly
- [ ] Accessibility notes included

---

*Last updated: 2026-01-29*
