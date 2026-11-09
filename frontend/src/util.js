export const SOURCE_LABELS = {
  property_portal: "Property portal",
  social_ad: "Social ad",
  website: "Website",
  hoarding_call: "Hoarding call",
};

export const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी" },
  { value: "gu", label: "ગુજરાતી" },
];

export function fmtDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-IN", {
    weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
  });
}

export function fmtDay(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
}

export function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}

export function fmtDuration(seconds) {
  if (seconds == null) return "n/a";
  if (seconds < 60) return `${seconds} s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s ? `${m} min ${s} s` : `${m} min`;
}

export function fmtINR(n) {
  return n == null ? "n/a" : "₹" + Number(n).toLocaleString("en-IN");
}

export function fmtPct(x) {
  return x == null ? "n/a" : Math.round(x * 100) + "%";
}
