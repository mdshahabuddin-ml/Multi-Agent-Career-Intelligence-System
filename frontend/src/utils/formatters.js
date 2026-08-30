export function formatDate(date) {
    if (!date) {
        return "N/A";
    }

    return new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(date));
}


export function formatPercentage(value) {
    if (value === null || value === undefined) {
        return "N/A";
    }

    return `${Math.round(value)}%`;
}


export function truncateText(
    text,
    maxLength = 150
) {
    if (!text) {
        return "";
    }

    if (text.length <= maxLength) {
        return text;
    }

    return `${text.substring(0, maxLength)}...`;
}