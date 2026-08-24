"use client";

export default function LoadingSpinner({
  size = "md",
  text,
}: {
  size?: "sm" | "md" | "lg";
  text?: string;
}) {
  const sizes = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8">
      <div
        className={`${sizes[size]} animate-spin rounded-full border-2 border-gray-700 border-t-blue-500`}
      />
      {text && <p className="text-sm text-gray-400">{text}</p>}
    </div>
  );
}
