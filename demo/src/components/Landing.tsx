import { motion } from "framer-motion";
import { Gavel, Scale, ExternalLink, ShieldAlert, Users, BookMarked, Info } from "lucide-react";
import { STATS, CASES, PERSONAS, CITATIONS, SCOPE_NOTE } from "../lib/content";

const fadeUp = {
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.5, ease: "easeOut" },
};

function SectionHead({ kicker, title, sub }: { kicker: string; title: string; sub?: string }) {
  return (
    <div className="mb-8 max-w-2xl">
      <div className="text-xs font-600 uppercase tracking-[0.2em] text-gold-500">{kicker}</div>
      <h2 className="mt-2 font-display text-3xl font-700 tracking-tight sm:text-4xl">{title}</h2>
      {sub && <p className="mt-3 text-slate-400">{sub}</p>}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="mx-auto max-w-6xl px-5">
      {/* Stats strip */}
      <motion.div {...fadeUp} className="grid grid-cols-2 gap-3 border-y border-ink-600 py-6 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="text-center sm:text-left">
            <div className="font-display text-2xl font-700 tabular text-gold-400 sm:text-3xl">{s.value}</div>
            <div className="mt-1 text-sm font-500 text-slate-200">{s.label}</div>
            <div className="text-xs text-slate-500">{s.sub}</div>
          </div>
        ))}
      </motion.div>

      {/* Why now — enforcement cases */}
      <section className="py-16">
        <motion.div {...fadeUp}>
          <SectionHead
            kicker="Why now"
            title="The law landed. Evidence collection is the bottleneck."
            sub="The FTC's Unfair or Deceptive Fees Rule took effect May 12, 2025. In 14 months, three landmark actions hit — and a dedicated rental-fee rule is now being written."
          />
        </motion.div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {CASES.map((c, i) => (
            <motion.a
              key={c.org}
              {...fadeUp}
              transition={{ ...fadeUp.transition, delay: i * 0.08 }}
              href={c.href}
              target="_blank"
              rel="noreferrer"
              className="group flex flex-col rounded-2xl border border-ink-600 bg-ink-800/70 p-5 transition-colors hover:border-gold-500/50"
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 font-display text-lg font-700">
                  <Gavel className="h-4.5 w-4.5 text-gold-400" /> {c.org}
                </span>
                <ExternalLink className="h-4 w-4 text-slate-600 transition-colors group-hover:text-gold-400" />
              </div>
              <div className="mt-3 font-display text-2xl font-700 text-slate-50">{c.amount}</div>
              <div className="mt-0.5 font-mono text-xs text-slate-500">{c.date} · {c.authority}</div>
              <p className="mt-3 text-sm leading-relaxed text-slate-400">{c.detail}</p>
            </motion.a>
          ))}
        </div>

        <motion.div {...fadeUp} className="mt-6 flex items-start gap-3 rounded-2xl border border-ink-600 bg-ink-900/60 p-4 text-sm text-slate-400">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-gold-500" />
          <p>{SCOPE_NOTE}</p>
        </motion.div>
      </section>

      {/* Personas */}
      <section className="py-12">
        <motion.div {...fadeUp}>
          <SectionHead kicker="Who pays" title="Three buyers, one evidence engine" />
        </motion.div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {PERSONAS.map((p, i) => {
            const Icon = [Users, ShieldAlert, Scale][i];
            return (
              <motion.div
                key={p.title}
                {...fadeUp}
                transition={{ ...fadeUp.transition, delay: i * 0.08 }}
                className="rounded-2xl border border-ink-600 bg-ink-800/70 p-5"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gold-500/15 text-gold-400">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mt-3 font-display text-lg font-700">{p.title}</h3>
                <p className="text-xs text-slate-500">{p.who}</p>
                <dl className="mt-4 space-y-2 text-sm">
                  <div><dt className="text-slate-500">Need</dt><dd className="text-slate-300">{p.need}</dd></div>
                  <div><dt className="text-slate-500">Value</dt><dd className="text-slate-300">{p.value}</dd></div>
                </dl>
                <div className="mt-4 rounded-lg border border-gold-600/30 bg-gold-500/5 px-3 py-1.5 text-center font-mono text-xs text-gold-400">
                  {p.price}
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* References */}
      <section className="py-12">
        <motion.div {...fadeUp}>
          <SectionHead kicker="Defensible" title="Primary sources" sub="Every claim above traces to a primary regulator source." />
        </motion.div>
        <motion.ul {...fadeUp} className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {CITATIONS.map((c) => (
            <li key={c.href}>
              <a
                href={c.href}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800/50 px-3 py-2 text-sm text-slate-300 transition-colors hover:border-gold-500/50 hover:text-gold-400"
              >
                <BookMarked className="h-4 w-4 shrink-0 text-gold-600" />
                <span className="flex-1">{c.claim}</span>
                <ExternalLink className="h-3.5 w-3.5 text-slate-600" />
              </a>
            </li>
          ))}
        </motion.ul>
      </section>
    </div>
  );
}
