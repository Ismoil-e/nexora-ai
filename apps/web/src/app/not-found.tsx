import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mb-4 text-8xl">🔍</div>
        <h1 className="mb-2 text-4xl font-bold text-white">404</h1>
        <p className="mb-2 text-lg text-gray-300">Sahifa topilmadi</p>
        <p className="mb-6 text-sm text-gray-500">
          Siz qidirgan sahifa mavjud emas yoki ko'chirilgan.
        </p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          Bosh sahifaga qaytish
        </Link>
      </div>
    </div>
  );
}
