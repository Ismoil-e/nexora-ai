"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[400px] items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mb-4 text-6xl">💥</div>
        <h2 className="mb-2 text-xl font-semibold text-white">
          Xatolik yuz berdi
        </h2>
        <p className="mb-2 text-sm text-gray-400">{error.message}</p>
        {error.digest && (
          <p className="mb-4 text-xs text-gray-600">ID: {error.digest}</p>
        )}
        <button
          onClick={reset}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          Qayta urinish
        </button>
      </div>
    </div>
  );
}
