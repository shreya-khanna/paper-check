# Paper Check frontend

    npm install
    npm run dev

Open http://localhost:3000. Without a backend it shows demo data.

To connect your backend, copy `.env.example` to `.env.local` and set `BACKEND_URL`.
Your service needs a `POST /analyze` endpoint that accepts multipart form data
(`identifier` text field or `file` PDF) and returns JSON matching `Report` in `lib/types.ts`.
