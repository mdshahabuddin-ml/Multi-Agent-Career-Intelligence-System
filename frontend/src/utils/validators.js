export function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
        email
    );
}


export function isValidPassword(password) {
    return (
        typeof password === "string" &&
        password.length >= 8
    );
}


export function required(value) {
    return (
        value !== null &&
        value !== undefined &&
        String(value).trim().length > 0
    );
}