function ErrorMessage({
  message = "Something went wrong.",
}) {
  return (
    <div className="error-message">
      <strong>Error:</strong>{" "}
      {message}
    </div>
  );
}


export default ErrorMessage;