import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
np.random.seed(42)

CRITICAL_ISSUES = [
    {"issue_key": "CRIT-001", "title": "System crash on production server", "description": "The production server crashes intermittently causing complete service outage. Critical business operations are affected. Need immediate investigation and fix."},
    {"issue_key": "CRIT-002", "title": "Database connection pool exhausted", "description": "Application cannot connect to database after 10 minutes of uptime. All users get connection errors. This is a critical production issue."},
    {"issue_key": "CRIT-003", "title": "Security vulnerability in authentication", "description": "SQL injection vulnerability discovered in login form. Immediate patch required to prevent unauthorized access."},
    {"issue_key": "CRIT-004", "title": "Payment processing failure", "description": "All credit card transactions are failing. Revenue impact is significant. Need hotfix deployment immediately."},
    {"issue_key": "CRIT-005", "title": "Data loss during backup", "description": "Scheduled backup corrupted database files. Critical customer data may be lost. Need recovery plan ASAP."},
    {"issue_key": "CRIT-006", "title": "API returning 500 errors", "description": "REST API endpoints returning 500 Internal Server Error for all requests. Mobile app is completely non-functional."},
    {"issue_key": "CRIT-007", "title": "Memory leak causing OOM crashes", "description": "Application memory usage grows unbounded until JVM crashes with OutOfMemoryError. Service restarts every few hours."},
    {"issue_key": "CRIT-008", "title": "SSL certificate expired", "description": "Production SSL certificate expired. Website showing security warnings to all users. Traffic dropping rapidly."},
    {"issue_key": "CRIT-009", "title": "Race condition in transaction processing", "description": "Double charges being processed due to race condition. Multiple customer complaints received. Need urgent fix."},
    {"issue_key": "CRIT-010", "title": "Critical data corruption", "description": "Database records being overwritten with null values. Customer orders disappearing from system. Emergency fix needed."},
    {"issue_key": "CRIT-011", "title": "Load balancer misconfiguration", "description": "Traffic not being distributed correctly. Some servers overloaded while others idle. Service degraded."},
    {"issue_key": "CRIT-012", "title": "Cache invalidation bug", "description": "Stale cache serving incorrect prices to customers. Wrong amounts charged. Immediate rollback required."},
    {"issue_key": "CRIT-013", "title": "Third-party API integration down", "description": "Payment gateway API returning errors. Cannot process any transactions. Affects all customers globally."},
    {"issue_key": "CRIT-014", "title": "Service bus message loss", "description": "Critical messages being dropped from message queue. Orders not being processed. Customer notifications failing."},
    {"issue_key": "CRIT-015", "title": "Cron job not executing", "description": "Scheduled batch jobs not running. Daily reports not generated. End-of-day processing failing."},
    {"issue_key": "CRIT-016", "title": "File storage quota exceeded", "description": "Upload functionality broken due to storage quota. Users cannot upload documents. Blocking business operations."},
    {"issue_key": "CRIT-017", "title": "Email notification system down", "description": "Transactional emails not being sent. Users not receiving password resets or order confirmations."},
    {"issue_key": "CRIT-018", "title": "Search index corrupted", "description": "Search functionality returning no results. Users cannot find products. Conversion rate dropping significantly."},
    {"issue_key": "CRIT-019", "title": "Admin panel inaccessible", "description": "System administrators cannot access admin panel. Cannot manage users or content. Security risk."},
    {"issue_key": "CRIT-020", "title": "WebSocket connection failures", "description": "Real-time updates not working. Chat and notifications broken. User engagement severely impacted."},
    {"issue_key": "CRIT-021", "title": "CDN configuration error", "description": "Static assets not loading. Website completely broken. All assets returning 404 errors."},
    {"issue_key": "CRIT-022", "title": "Backup restoration failed", "description": "Disaster recovery test failed. Cannot restore from backups. Business continuity at risk."},
    {"issue_key": "CRIT-023", "title": "DNS resolution failure", "description": "Domain not resolving to server. Website completely inaccessible. Affecting all users worldwide."},
    {"issue_key": "CRIT-024", "title": "Session management broken", "description": "Users being logged out immediately. Cannot maintain login state. All user sessions affected."},
    {"issue_key": "CRIT-025", "title": "Rate limiting too aggressive", "description": "Legitimate users being blocked by rate limiter. Service effectively unusable for real users."},
    {"issue_key": "CRIT-026", "title": "Database migration failure", "description": "Schema migration corrupted table structure. Application cannot read data. Emergency rollback needed."},
    {"issue_key": "CRIT-027", "title": "Encryption key compromised", "description": "Encryption keys exposed in logs. All sensitive data potentially compromised. Need key rotation."},
    {"issue_key": "CRIT-028", "title": "Monitoring system alerts failing", "description": "No alerts being sent when services go down. Outages going unnoticed for hours."},
    {"issue_key": "CRIT-029", "title": "Container orchestration failure", "description": "Kubernetes pods not scheduling correctly. Services running on insufficient resources. Performance degraded."},
    {"issue_key": "CRIT-030", "title": "Code deployment broke authentication", "description": "Latest deployment broke login flow. No users can authenticate. Need immediate rollback."},
    {"issue_key": "CRIT-031", "title": "Database deadlock causing timeouts", "description": "Deadlocks causing request timeouts. Application unresponsive during peak hours."},
    {"issue_key": "CRIT-032", "title": "API rate limit not working", "description": "Rate limiting completely broken. Server overloaded by malicious bot traffic."},
    {"issue_key": "CRIT-033", "title": "File upload size limit too small", "description": "Users cannot upload files over 1MB. Business users need to upload larger documents."},
    {"issue_key": "CRIT-034", "title": "Background job queue stuck", "description": "All background jobs queued but not executing. Data processing completely halted."},
    {"issue_key": "CRIT-035", "title": "Timezone handling incorrect", "description": "All timestamps off by hours due to timezone bug. Reports contain wrong dates."},
    {"issue_key": "CRIT-036", "title": "Pagination returning duplicates", "description": "List endpoints returning duplicate records. Users seeing same items multiple times."},
    {"issue_key": "CRIT-037", "title": "Validation bypass vulnerability", "description": "Input validation not working. Malformed data entering system. Potential security issue."},
    {"issue_key": "CRIT-038", "title": "Mobile app sync broken", "description": "Mobile app cannot sync with server. Offline mode not working. User data lost."},
    {"issue_key": "CRIT-039", "title": "Webhook delivery failures", "description": "Third-party webhooks not being delivered. Integration partners complaining."},
    {"issue_key": "CRIT-040", "title": "SSO authentication loop", "description": "Users stuck in redirect loop during SSO login. Cannot access application."},
    {"issue_key": "CRIT-041", "title": "Report generation timeout", "description": "Large reports timing out. Business users cannot access important data."},
    {"issue_key": "CRIT-042", "title": "GraphQL query depth limit missing", "description": "Malicious queries causing server resource exhaustion. Need query complexity limits."},
    {"issue_key": "CRIT-043", "title": "Custom domain SSL not working", "description": "Custom domains showing certificate errors. Partner integrations broken."},
    {"issue_key": "CRIT-044", "title": "Push notification certificates expired", "description": "iOS and Android push notifications not working. User engagement down significantly."},
    {"issue_key": "CRIT-045", "title": "Database query plan caching bug", "description": "Query performance degrading over time. Need to restart database daily."},
    {"issue_key": "CRIT-046", "title": "Audit log gap detected", "description": "Security audit logs have gaps. Cannot track user actions. Compliance risk."},
    {"issue_key": "CRIT-047", "title": "Microservice health checks failing", "description": "Health check endpoints returning false negatives. Load balancer removing healthy instances."},
    {"issue_key": "CRIT-048", "title": "Feature flag system down", "description": "Cannot toggle features on/off. Cannot do gradual rollouts. Deployment blocked."},
    {"issue_key": "CRIT-049", "title": "Object storage bucket full", "description": "File storage at capacity. Cannot accept new uploads. Business operations halted."},
    {"issue_key": "CRIT-050", "title": "APM agent causing latency", "description": "Application performance monitoring adding 500ms latency to every request."},
]

MAJOR_ISSUES = [
    {"issue_key": "MAJR-001", "title": "Performance degradation under load", "description": "Page load times increased from 2s to 8s during peak hours. Users complaining about slowness."},
    {"issue_key": "MAJR-002", "title": "Search results not relevant", "description": "Search algorithm returning irrelevant results. Users cannot find what they need. Bounce rate increasing."},
    {"issue_key": "MAJR-003", "title": "Mobile app crashes on Android 14", "description": "App crashes immediately on devices running Android 14. Significant user impact."},
    {"issue_key": "MAJR-004", "title": "Export to CSV producing duplicates", "description": "When exporting large datasets, duplicate rows appear in CSV. Data integrity concern."},
    {"issue_key": "MAJR-005", "title": "Dashboard widgets not loading", "description": "Dashboard shows loading spinner indefinitely for some widgets. No data displayed."},
    {"issue_key": "MAJR-006", "title": "Image upload failing for large files", "description": "Files over 5MB fail to upload with timeout error. Need to increase limit or optimize."},
    {"issue_key": "MAJR-007", "title": "Date filter not working in reports", "description": "Date range filter in reports ignores user input. Always shows default range."},
    {"issue_key": "MAJR-008", "title": "PDF generation missing logos", "description": "Generated PDFs missing company logo. Brand consistency issue in customer communications."},
    {"issue_key": "MAJR-009", "title": "Sorting not persisting in tables", "description": "User sorts table by column but sort order resets on page refresh. Poor UX."},
    {"issue_key": "MAJR-010", "title": "Email templates showing raw HTML", "description": "Some email clients displaying HTML source instead of rendered content. Requires fix."},
    {"issue_key": "MAJR-011", "title": "API documentation outdated", "description": "API docs show endpoints that no longer exist. Confusing for developers."},
    {"issue_key": "MAJR-012", "title": "Filter dropdown showing deleted options", "description": "Filter dropdown includes options for deleted categories. Selecting them returns empty results."},
    {"issue_key": "MAJR-013", "title": "Chart tooltips not displaying", "description": "Hovering over chart data points shows no tooltip. Cannot see exact values."},
    {"issue_key": "MAJR-014", "title": "Bulk actions timing out", "description": "Selecting more than 100 items for bulk update causes timeout. Need pagination."},
    {"issue_key": "MAJR-015", "title": "User profile picture not updating", "description": "Uploaded profile picture not appearing. Old image remains cached."},
    {"issue_key": "MAJR-016", "title": "Two-factor auth QR code scanning fails", "description": "Google Authenticator cannot scan QR code. Users cannot enable 2FA."},
    {"issue_key": "MAJR-017", "title": "Breadcrumb navigation broken", "description": "Breadcrumbs show incorrect parent pages. Users get lost navigating hierarchy."},
    {"issue_key": "MAJR-018", "title": "Dark mode has contrast issues", "description": "Some text in dark mode is hard to read. Contrast ratio below accessibility standards."},
    {"issue_key": "MAJR-019", "title": "Calendar events showing wrong timezone", "description": "Events display in UTC instead of user's timezone. Confusion for scheduling."},
    {"issue_key": "MAJR-020", "title": "Autocomplete suggestions slow", "description": "Type-ahead suggestions take 3+ seconds to appear. Should be near-instant."},
    {"issue_key": "MAJR-021", "title": "Form validation messages unclear", "description": "Error messages don't explain what went wrong. Users confused about fixes."},
    {"issue_key": "MAJR-022", "title": "File browser navigation slow", "description": "Browsing through folders takes 5+ seconds per action. Needs optimization."},
    {"issue_key": "MAJR-023", "title": "Comments not loading on posts", "description": "Comment section shows loading spinner forever. Cannot view or add comments."},
    {"issue_key": "MAJR-024", "title": "Video playback buffering constantly", "description": "Embedded videos buffer every few seconds. Unwatchable experience."},
    {"issue_key": "MAJR-025", "title": "RSS feed not updating", "description": "RSS feed shows stale content. New posts not appearing in feed readers."},
    {"issue_key": "MAJR-026", "title": "Webhook retry logic broken", "description": "Failed webhooks not being retried. External systems not receiving updates."},
    {"issue_key": "MAJR-027", "title": "Admin cannot see all user roles", "description": "User management page truncates role names. Cannot distinguish permissions."},
    {"issue_key": "MAJR-028", "title": "API rate limit counter inaccurate", "description": "Rate limit headers show wrong numbers. Confusing for API consumers."},
    {"issue_key": "MAJR-029", "title": "Print stylesheet missing", "description": "Pages print poorly. Content runs off pages. Need print-optimized styles."},
    {"issue_key": "MAJR-030", "title": "Markdown rendering inconsistent", "description": "Some markdown syntax renders correctly, some doesn't. Inconsistent user content."},
    {"issue_key": "MAJR-031", "title": "Data table sticky header not working", "description": "Table header scrolls away on long lists. Hard to read data."},
    {"issue_key": "MAJR-032", "title": "Currency formatting incorrect", "description": "Some currencies display wrong symbols. Euro showing as dollar sign."},
    {"issue_key": "MAJR-033", "title": "Timeago displaying wrong times", "description": "\"5 minutes ago\" shows for items from hours ago. Cache invalidation issue."},
    {"issue_key": "MAJR-034", "title": "Infinite scroll pagination broken", "description": "Loading more items replaces existing items instead of appending. Data loss."},
    {"issue_key": "MAJR-035", "title": "OAuth token refresh failing", "description": "Access tokens not being refreshed. Users logged out unexpectedly after 1 hour."},
    {"issue_key": "MAJR-036", "title": "Data visualization colors wrong", "description": "Chart colors don't match legend. Misleading data representation."},
    {"issue_key": "MAJR-037", "title": "Keyboard shortcuts not working", "description": "Ctrl+S and other shortcuts have no effect. Power user feature broken."},
    {"issue_key": "MAJR-038", "title": "Pagination state not in URL", "description": "Page number not reflected in URL. Sharing links doesn't work correctly."},
    {"issue_key": "MAJR-039", "title": "File preview not generating", "description": "Preview thumbnails not showing for uploaded files. Users must download to view."},
    {"issue_key": "MAJR-040", "title": "Tag suggestions from wrong dataset", "description": "Auto-suggested tags are irrelevant. ML model needs retraining."},
    {"issue_key": "MAJR-041", "title": "Modal dialogs not closing on backdrop click", "description": "Clicking outside modal doesn't close it. Inconsistent with UX expectations."},
    {"issue_key": "MAJR-042", "title": "CSV import mapping not saving", "description": "Column mappings not persisted between imports. Users redo setup each time."},
    {"issue_key": "MAJR-043", "title": "Progress bar inaccurate", "description": "Upload progress shows 100% before completion. Confusing feedback."},
    {"issue_key": "MAJR-044", "title": "Favicon not displaying in browser tab", "description": "Site icon missing. Brand visibility issue across browser tabs."},
    {"issue_key": "MAJR-045", "title": "JSON API returning XML content-type", "description": "API responses have wrong Content-Type header. Breaks some HTTP clients."},
    {"issue_key": "MAJR-046", "title": "Tab order in forms incorrect", "description": "Tab key jumps to unexpected fields. Accessibility and UX issue."},
    {"issue_key": "MAJR-047", "title": "Batch delete confirmation unclear", "description": "Delete confirmation doesn't show how many items will be affected. Safety concern."},
    {"issue_key": "MAJR-048", "title": "Tooltips truncated on overflow", "description": "Long tooltips get cut off. Cannot read full message."},
    {"issue_key": "MAJR-049", "title": "Responsive menu broken on tablet", "description": "Navigation menu doesn't work properly on iPad. Touch targets too small."},
    {"issue_key": "MAJR-050", "title": "Error logs not rotated", "description": "Log files growing unbounded. Disk space will be exhausted soon."},
]

MINOR_ISSUES = [
    {"issue_key": "MINR-001", "title": "Typos in error messages", "description": "Several error messages have spelling mistakes. Should be corrected for professionalism."},
    {"issue_key": "MINR-002", "title": "Minor spacing inconsistency in footer", "description": "Footer links have uneven spacing. Visual polish issue."},
    {"issue_key": "MINR-003", "title": "Placeholder text not localized", "description": "Form placeholders show English text for non-English locales."},
    {"issue_key": "MINR-004", "title": "Loading spinner slightly off-center", "description": "Spinner icon misaligned by 2 pixels. Minor visual issue."},
    {"issue_key": "MINR-005", "title": "Unused console.log statements in JS", "description": "Debug logging left in production code. Should be removed for cleanliness."},
    {"issue_key": "MINR-006", "title": "Alt text missing on decorative images", "description": "Decorative images should have empty alt attribute for accessibility."},
    {"issue_key": "MINR-007", "title": "Timestamp showing seconds when not needed", "description": "Dates show unnecessary precision. Should round to nearest minute."},
    {"issue_key": "MINR-008", "title": "Button hover state barely visible", "description": "Hover color change too subtle. Users may not notice interaction."},
    {"issue_key": "MINR-009", "title": "Unnecessary scrollbar appearing", "description": "Vertical scrollbar shows even when content fits. Minor visual distraction."},
    {"issue_key": "MINR-010", "title": "Favicon cache not clearing on update", "description": "New favicon doesn't show until cache cleared. Minor deployment issue."},
    {"issue_key": "MINR-011", "title": "Debug info visible in footer", "description": "Development environment info showing in production footer."},
    {"issue_key": "MINR-012", "title": "Text selection color inconsistent", "description": "Highlight color different across browsers. Should standardize."},
    {"issue_key": "MINR-013", "title": "Help icon tooltip slightly delayed", "description": "Info tooltips take 1 second to appear. Slight UX improvement."},
    {"issue_key": "MINR-014", "title": "Breadcrumb separator inconsistent", "description": "Some separators are pipes, others are chevrons. Should standardize."},
    {"issue_key": "MINR-015", "title": "Login page logo slightly blurry", "description": "Logo resolution not optimal on retina displays. Minor visual quality issue."},
    {"issue_key": "MINR-016", "title": "Warning banner border-radius mismatch", "description": "Warning box has different corner radius than error/success boxes."},
    {"issue_key": "MINR-017", "title": "Unused CSS selectors in stylesheet", "description": "Stylesheet contains dead code. Should be cleaned up."},
    {"issue_key": "MINR-018", "title": "Page title doesn't match heading", "description": "Browser tab title slightly different from page H1. Minor inconsistency."},
    {"issue_key": "MINR-019", "title": "Empty state illustration not centered", "description": "Empty state graphic slightly off-center on wide screens."},
    {"issue_key": "MINR-020", "title": "Form labels slightly misaligned", "description": "Labels are 1px out of alignment with inputs. Minor visual polish."},
    {"issue_key": "MINR-021", "title": "Tooltip arrow pointing slightly off", "description": "Tooltip pointer not perfectly aligned with trigger element."},
    {"issue_key": "MINR-022", "title": "Disabled button still clickable briefly", "description": "Click event fires before button becomes disabled. Race condition."},
    {"issue_key": "MINR-023", "title": "Notification badge slightly mispositioned", "description": "Notification count badge is 1px too high. Minor positioning fix."},
    {"issue_key": "MINR-024", "title": "Table row hover effect too subtle", "description": "Row highlight on hover barely visible. Should be more obvious."},
    {"issue_key": "MINR-025", "title": "Link underline style inconsistent", "description": "Some links have underlines, others don't. Need consistent styling."},
    {"issue_key": "MINR-026", "title": "Modal close button slightly small", "description": "X button in modal is 2px smaller than design spec."},
    {"issue_key": "MINR-027", "title": "Font weight slightly different on mobile", "description": "Headings appear bolder on mobile devices. Rendering difference."},
    {"issue_key": "MINR-028", "title": "Padding inconsistent in card components", "description": "Some cards have 16px padding, others 15px. Should standardize."},
    {"issue_key": "MINR-029", "title": "Search icon color contrast low", "description": "Search icon doesn't meet WCAG contrast requirements. Minor accessibility."},
    {"issue_key": "MINR-030", "title": "Progress bar color slightly off-brand", "description": "Progress indicator is 2% lighter than brand color."},
    {"issue_key": "MINR-031", "title": "Dropdown arrow not vertically centered", "description": "Select dropdown arrow is 1px too high."},
    {"issue_key": "MINR-032", "title": "Focus ring color not matching design", "description": "Keyboard focus indicator uses wrong shade of blue."},
    {"issue_key": "MINR-033", "title": "Avatar placeholder showing initials wrong", "description": "User initials display in wrong order for multi-word names."},
    {"issue_key": "MINR-034", "title": "Checkbox checkmark slightly thin", "description": "Checkmark in checkbox is 1px thinner than design spec."},
    {"issue_key": "MINR-035", "title": "Success toast timeout inconsistent", "description": "Success messages disappear at different intervals. Should standardize."},
    {"issue_key": "MINR-036", "title": "Tab underline animation jerky", "description": "Tab switch animation has slight stutter. Could be smoothed."},
    {"issue_key": "MINR-037", "title": "Date picker year dropdown too narrow", "description": "Year selector truncates 4-digit years in some locales."},
    {"issue_key": "MINR-038", "title": "Breadcrumb truncation inconsistent", "description": "Long paths truncated at different lengths. Should standardize."},
    {"issue_key": "MINR-039", "title": "Skeleton loader animation slightly fast", "description": "Loading placeholder animation feels slightly rushed. Minor UX tweak."},
    {"issue_key": "MINR-040", "title": "Section divider line too light", "description": "Horizontal rules are barely visible. Should increase opacity."},
    {"issue_key": "MINR-041", "title": "Card shadow depth inconsistent", "description": "Some cards have stronger shadows than others. Should match."},
    {"issue_key": "MINR-042", "title": "Icon button size slightly off", "description": "Icon-only buttons are 2px larger than specified."},
    {"issue_key": "MINR-043", "title": "Status indicator pulse animation slow", "description": "Online status dot pulses slower than other indicators."},
    {"issue_key": "MINR-044", "title": "Description text line height tight", "description": "Body text line height is 0.1 less than recommended."},
    {"issue_key": "MINR-045", "title": "Mobile menu icon line spacing wrong", "description": "Hamburger menu lines have incorrect spacing."},
    {"issue_key": "MINR-046", "title": "Star rating component half-star off", "description": "Half-star ratings display incorrectly for some values."},
    {"issue_key": "MINR-047", "title": "Tag background color saturation low", "description": "Tag colors appear more muted than design mocks."},
    {"issue_key": "MINR-048", "title": "Footer links underline animation slow", "description": "Link underline animation takes 300ms instead of 200ms."},
    {"issue_key": "MINR-049", "title": "Profile dropdown z-index too low", "description": "User menu appears behind some page elements occasionally."},
    {"issue_key": "MINR-050", "title": "Toast notification position slightly high", "description": "Notifications appear 4px higher than specified."},
]

TRIVIAL_ISSUES = [
    {"issue_key": "TRIV-001", "title": "Typo in footer copyright year", "description": "Copyright shows 2024 instead of 2026. Minor text correction."},
    {"issue_key": "TRIV-002", "title": "Extra space after paragraph in about page", "description": "About page has double line break in one spot. Simple formatting fix."},
    {"issue_key": "TRIV-003", "title": "Capitalization inconsistency in menu", "description": "Menu items have mixed case styles. Should standardize to title case."},
    {"issue_key": "TRIV-004", "title": "Favicon shows old logo version", "description": "Browser tab icon is still the old logo. Already updated elsewhere."},
    {"issue_key": "TRIV-005", "title": "Minor grammatical error in tooltip", "description": "Help text has small grammar issue. Should say 'an' not 'a'."},
    {"issue_key": "TRIV-006", "title": "Missing Oxford comma in sentences", "description": "Text lacks serial comma in several places. Style consistency."},
    {"issue_key": "TRIV-007", "title": "Whitespace inconsistency in source code", "description": "Code indentation uses mixed tabs and spaces. Cleanup task."},
    {"issue_key": "TRIV-008", "title": "Commented-out code in template", "description": "Old commented code left in HTML template. Should be removed."},
    {"issue_key": "TRIV-009", "title": "Console warning on page load", "description": "Browser console shows minor deprecation warning. Low priority."},
    {"issue_key": "TRIV-010", "title": "Unused variable in JavaScript", "description": "Code contains declared but unused variable. Should clean up."},
    {"issue_key": "TRIV-011", "title": "Date format using US style globally", "description": "Dates show MM/DD/YYYY even for international users. Low priority i18n."},
    {"issue_key": "TRIV-012", "title": "Placeholder text has typo", "description": "Search placeholder says 'Searc' missing 'h'. Simple typo fix."},
    {"issue_key": "TRIV-013", "title": "Dev dependency in package.json", "description": "Development-only package included in production bundle. Bundle size impact minimal."},
    {"issue_key": "TRIV-014", "title": "Missing semicolon in JS file", "description": "JavaScript missing semicolon after statement. Linting issue."},
    {"issue_key": "TRIV-015", "title": "Image alt text says 'image' generically", "description": "All images have generic alt text. Should be more descriptive."},
    {"issue_key": "TRIV-016", "title": "Button text not centered vertically", "description": "Button labels are 1px off-center. Visual polish."},
    {"issue_key": "TRIV-017", "title": "Hyperlink color slightly off-brand", "description": "Links are #0066CC instead of #0066CC. Barely noticeable."},
    {"issue_key": "TRIV-018", "title": "Unused CSS class in stylesheet", "description": "Style file has selectors for removed UI elements."},
    {"issue_key": "TRIV-019", "title": "Page load time 100ms slower than optimal", "description": "Minor performance improvement opportunity. Not urgent."},
    {"issue_key": "TRIV-020", "title": "Email address in footer needs update", "description": "Support email changed. Footer has old address."},
    {"issue_key": "TRIV-021", "title": "Copyright company name slightly wrong", "description": "Company name has extra space in footer."},
    {"issue_key": "TRIV-022", "title": "Redundant HTTP request on page load", "description": "Page makes unnecessary API call. Low priority optimization."},
    {"issue_key": "TRIV-023", "title": "Analytics event tracking misspelled", "description": "Event name has typo in tracking code."},
    {"issue_key": "TRIV-024", "title": "Help text punctuation inconsistency", "description": "Some help sentences end with periods, others don't."},
    {"issue_key": "TRIV-025", "title": "Console error on legacy browser", "description": "Minor JS error on IE11. Small user base affected."},
    {"issue_key": "TRIV-026", "title": "Unused import in React component", "description": "Component imports but doesn't use a function. Code cleanup."},
    {"issue_key": "TRIV-027", "title": "Meta description slightly over character limit", "description": "SEO description 10 characters over optimal length."},
    {"issue_key": "TRIV-028", "title": "Favicon not showing in dark mode", "description": "Light favicon doesn't show well on dark browser tabs."},
    {"issue_key": "TRIV-029", "title": "Duplicate key in translation file", "description": "i18n file has redundant entry. Should deduplicate."},
    {"issue_key": "TRIV-030", "title": "Text shadow on heading too subtle", "description": "Title text shadow barely visible. Design preference."},
    {"issue_key": "TRIV-031", "title": "Missing aria-label on icon button", "description": "Screen readers can't identify icon-only button purpose."},
    {"issue_key": "TRIV-032", "title": "Cache headers slightly misconfigured", "description": "Static assets cached 1 hour less than optimal."},
    {"issue_key": "TRIV-033", "title": "Console log in production code", "description": "Debug statement left in. Low priority cleanup."},
    {"issue_key": "TRIV-034", "title": "Social share icons slightly misaligned", "description": "Share buttons are 1px out of horizontal alignment."},
    {"issue_key": "TRIV-035", "title": "Breadcrumb separator uses wrong character", "description": "Breadcrumb uses '>' instead of '/' for separator."},
    {"issue_key": "TRIV-036", "title": "Table header background not consistent", "description": "Some table headers have different background shades."},
    {"issue_key": "TRIV-037", "title": "Tooltip appears 50ms slower than spec", "description": "Delayed tooltip feels unresponsive. Minor UX."},
    {"issue_key": "TRIV-038", "title": "Empty state text could be friendlier", "description": "Copy could be more welcoming. Content improvement."},
    {"issue_key": "TRIV-039", "title": "Success message not including emoji", "description": "Brand guidelines recommend emoji in success messages."},
    {"issue_key": "TRIV-040", "title": "Mobile viewport meta tag order", "description": "Meta tags in wrong order. Works but not ideal."},
    {"issue_key": "TRIV-041", "title": "Button border-radius 1px inconsistent", "description": "Some buttons have 4px radius, others 3px."},
    {"issue_key": "TRIV-042", "title": "Heading hierarchy has skipped level", "description": "Page goes from H1 to H3. Should use H2."},
    {"issue_key": "TRIV-043", "title": "Unused sprite in image sprite sheet", "description": "Old icons still in sprite. Minor file size."},
    {"issue_key": "TRIV-044", "title": "Input placeholder color contrast low", "description": "Placeholder text slightly hard to read."},
    {"issue_key": "TRIV-045", "title": "Tab index order not optimal", "description": "Keyboard navigation could be more logical. Minor a11y."},
    {"issue_key": "TRIV-046", "title": "Footer background color slightly wrong", "description": "Footer is #F5F5F5 instead of #F8F8F8."},
    {"issue_key": "TRIV-047", "title": "Code comment describes wrong function", "description": "Comment refers to old function name. Misleading."},
    {"issue_key": "TRIV-048", "title": "Page jump link missing top padding", "description": "Anchor links don't account for fixed header."},
    {"issue_key": "TRIV-049", "title": "Social meta tags have minor issues", "description": "Open Graph image size slightly off spec."},
    {"issue_key": "TRIV-050", "title": "Cookie consent button slightly delayed", "description": "Accept button appears 200ms after page load."},
]

def create_jira_sample_data():
    all_issues = []
    
    for issue in CRITICAL_ISSUES[:50]:
        issue['priority'] = 'Critical'
        all_issues.append(issue)
    
    for issue in MAJOR_ISSUES[:50]:
        issue['priority'] = 'Major'
        all_issues.append(issue)
    
    for issue in MINOR_ISSUES[:50]:
        issue['priority'] = 'Minor'
        all_issues.append(issue)
    
    for issue in TRIVIAL_ISSUES[:50]:
        issue['priority'] = 'Trivial'
        all_issues.append(issue)
    
    return pd.DataFrame(all_issues)

if __name__ == "__main__":
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    
    print("Creating Jira sample dataset...")
    df = create_jira_sample_data()
    
    output_path = DATA_DIR / "jira_balanced_200.csv"
    df.to_csv(output_path, index=False)
    
    print(f"Jira dataset saved to {output_path}")
    print(f"Total issues: {len(df)}")
    print(f"Priority distribution:\n{df['priority'].value_counts()}")
