import { FormEvent, useState } from "react"
import {
  Building2,
  CheckCircle2,
  Cloud,
  Droplets,
  Handshake,
  Lightbulb,
  MapPin,
  Network,
  Phone,
  Send,
  Shield,
  ShieldCheck,
  SolarPanel,
  Users,
  Wrench,
} from "lucide-react"
import { Hero, SectionTitle } from "../components/PublicLayout"
import { useEffect } from "react"
import { api, errorMessage } from "../services/api"

const quickServices = [
  {
    icon: Network,
    title: "Télémétrie & Télésurveillance",
    lines: [
      "Surveillance temps réel des infrastructures",
      "Data fiable & reporting détaillé",
      "Solutions connectées pour Orange Mali",
    ],
  },
  {
    icon: Building2,
    title: "Génie Civil",
    lines: [
      "Terrassement & fondations",
      "Aménagements techniques sur mesure",
      "2G 3G 4G 5G, Fibre, VoIP",
    ],
  },
  {
    icon: Wrench,
    title: "Services environnementaux",
    lines: [
      "Chasse aux abeilles & désinfestation",
      "Défratation & traitement",
      "Prévention & suivi de sites",
    ],
  },
]

const InfoCard = ({
  icon: Icon,
  title,
  children,
  white = false,
}: {
  icon: any
  title: string
  children: React.ReactNode
  white?: boolean
}) => (
  <article className={`info-card ${white ? "white" : ""}`}>
    <Icon />
    <h3>{title}</h3>
    <div>{children}</div>
  </article>
)

export function Home() {
  return (
    <>
      <Hero
        eyebrow="ACCUEIL"
        title={"Bienvenue chez GLOBAL\nSERVICES TECHNOLOGIE"}
        subtitle="Votre partenaire technologique au Mali  surveillance temps réel · data fiable · solutions connectées"
      />
      <section className="content-section">
        <SectionTitle
          title="CHIFFRES CLÉS"
          subtitle="Notre impact en quelques chiffres"
        />
        <div className="cards three">
          <InfoCard icon={Network} title="100+ sites supervisés">
            <p>Surveillés 24/7 à travers le Mali</p>
          </InfoCard>
          <InfoCard icon={Shield} title="24/7 Surveillance">
            <p>Monitoring en temps réel continu</p>
          </InfoCard>
          <InfoCard icon={Handshake} title="4 partenaires majeurs">
            <p>Collaboration active au Mali</p>
          </InfoCard>
        </div>
        <SectionTitle
          title="NOS SERVICES RAPIDES"
          subtitle="Nos expertises principales à votre service"
        />
        <div className="cards three">
          {quickServices.map(({ icon, title, lines }) => (
            <InfoCard key={title} icon={icon} title={title}>
              {lines.map((x) => (
                <p key={x}>• {x}</p>
              ))}
            </InfoCard>
          ))}
        </div>
      </section>
    </>
  )
}

export function About() {
  return (
    <>
      <Hero
        eyebrow="À PROPOS"
        title="Qui sommes-nous ?"
        subtitle={"votre partenaire de confiance au Mali depuis\n2020"}
        description="Depuis 2020, nous accompagnons les entreprises et institutions maliennes avec des solutions technologiques fiables, innovantes et adaptées aux défis locaux. Notre engagement : sécuriser, connecter et optimiser les infrastructures pour un Mali plus résilient."
      />
      <section className="content-section">
        <SectionTitle
          title="NOTRE HISTOIRE"
          subtitle="Notre parcours depuis 2020"
        />
        <div className="cards three compact">
          <InfoCard icon={Network} title="Création 2020">
            <p>
              Fondation de GST à Bamako pour répondre aux besoins croissants en
              surveillance et solutions technologiques au Mali
            </p>
          </InfoCard>
          <InfoCard
            icon={Shield}
            title="Expertise télécom · énergie · environnementale"
          >
            <p>Des solutions sur mesure pour des infrastructures critiques</p>
          </InfoCard>
          <InfoCard icon={Handshake} title="Capital humain qualifié">
            <p>
              Une équipe d’ingénieurs et techniciens formés pour un service
              d’excellence
            </p>
          </InfoCard>
        </div>
        <SectionTitle
          title="NOTRE MISSION"
          subtitle="Notre engagement au quotidien"
        />
        <div className="cards three mission">
          <InfoCard
            white
            icon={Lightbulb}
            title="Fournir des solutions innovantes"
          >
            <p>
              Déployer des technologies modernes pour garantir performance et
              fiabilité
            </p>
          </InfoCard>
          <InfoCard white icon={ShieldCheck} title="Fiables & sécurisées">
            <p>Assurer la sécurité et la continuité des opérations 24/7</p>
          </InfoCard>
          <InfoCard white icon={Users} title="Proximité locale">
            <p>Un accompagnement réactif et proche de nos clients au Mali</p>
          </InfoCard>
        </div>
        <SectionTitle
          title="NOS VALEURS"
          subtitle="Les principes qui guident nos actions"
        />
        <div className="cards four">
          {[
            [
              Lightbulb,
              "Innovation",
              "Rechercher constamment des solutions nouvelles et performantes",
            ],
            [
              ShieldCheck,
              "Fiabilité",
              "Un engagement ferme pour des services stables et de qualité",
            ],
            [
              Shield,
              "Sécurité",
              "Priorité à la protection des données et des infrastructures",
            ],
            [
              Users,
              "Proximité",
              "Un accompagnement local, réactif et proche de nos clients",
            ],
          ].map(([I, t, d]: any) => (
            <InfoCard key={t} icon={I} title={t}>
              <p>{d}</p>
            </InfoCard>
          ))}
        </div>
      </section>
    </>
  )
}

const references = [
  [
    Network,
    "Orange Mali  Télésurveillance & Télémétrie énergétique",
    [
      "Déploiement système télémétrie sites télécoms",
      "Supervision 24/7  tableau de bord centralisé",
    ],
  ],
  [
    Droplets,
    "Curage & Baremage  cuves hydrocarbures",
    ["Intervention sur sites", "Maintenance préventive & curative"],
  ],
  [
    Building2,
    "Services Publics & ONG  Fourniture de carburant",
    ["Approvisionnement sécurisé", "Logistique & livraison sites"],
  ],
  [
    Building2,
    "IENG MALI  Génie Civil & infrastructures",
    ["Terrassement · supports · fondations", "2G 3G 4G 5G Fibre VoIP"],
  ],
  [
    Wrench,
    "IENG MALI  Services environnementaux",
    ["Chasse aux abeilles", "Traitement, prévention & suivi de sites"],
  ],
]
const ambitions = [
  [
    Network,
    "Optimisation réseaux télécoms",
    "2G · 3G · 4G · 5G · Fibre · VoIP",
  ],
  [Cloud, "Solutions Cloud & DevOps", "Migration · Hébergement · B2B · IoT"],
  [Shield, "Sécurité systèmes & RGPD", "Audit cybersécurité · PRA · PCA"],
  [
    SolarPanel,
    "Solutions énergétiques complètes",
    "Photovoltaïque · Hybridation · Batteries",
  ],
]

export function References() {
  return (
    <>
      <Hero
        title={"Télésurveillance & Télémétrie\nénergétique"}
        subtitle="Surveillance temps réel · data fiable · solutions connectées pour Orange Mali"
        description="Des solutions de supervision 24/7 pour sécuriser vos infrastructures et optimiser votre énergie, avec reporting en temps réel et interventions rapides sur l’ensemble du territoire malien."
        primary="Demander une démo"
        secondary="Voir nos références"
        primaryTo="/contact"
        secondaryTo="#references-list"
      />
      <section className="content-section" id="references-list">
        <SectionTitle
          title="NOS RÉFÉRENCES"
          subtitle="Nos réalisations avec nos partenaires"
        />
        <div className="cards five refs">
          {references.map(([I, t, lines]: any) => (
            <InfoCard white key={t} icon={I} title={t}>
              {lines.map((x: string) => (
                <p key={x}>• {x}</p>
              ))}
            </InfoCard>
          ))}
        </div>
        <SectionTitle
          title="NOS SERVICES D’AMBITIONS"
          subtitle="Nous avons le capital humain pour les réaliser"
        />
        <div className="cards four">
          {ambitions.map(([I, t, d]: any) => (
            <InfoCard key={t} icon={I} title={t}>
              <p>{d}</p>
            </InfoCard>
          ))}
        </div>
      </section>
    </>
  )
}

export function Services() {
  return (
    <>
      <Hero
        eyebrow="NOS SERVICES"
        title={"Des solutions fiables,\npensées pour le terrain"}
        subtitle="Télécoms · énergie · sécurité · infrastructures · environnement"
        description="GST réunit les compétences techniques nécessaires pour superviser, sécuriser et maintenir les infrastructures critiques de ses clients."
        primary="Demander une étude"
        primaryTo="/contact"
      />
      <section className="content-section services-page">
        <SectionTitle
          title="NOS DOMAINES D’EXPERTISE"
          subtitle="Une réponse complète, de l’étude à la maintenance"
        />
        <div className="cards three">
          {quickServices.map(({ icon, title, lines }) => (
            <InfoCard key={title} icon={icon} title={title}>
              <p>{lines.join(" · ")}</p>
            </InfoCard>
          ))}
          {ambitions.slice(1).map(([I, t, d]: any) => (
            <InfoCard key={t} icon={I} title={t}>
              <p>{d}</p>
            </InfoCard>
          ))}
        </div>
      </section>
    </>
  )
}

export function Contact() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    message: "",
    service: "Demande générale",
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [sent, setSent] = useState(false)
  const [website, setWebsite] = useState("") // honeypot, hidden from humans
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState("")
  const [serviceOptions, setServiceOptions] = useState<string[]>([
    "Télésurveillance", "Télémétrie énergétique", "Génie civil", "Services environnementaux",
  ])
  useEffect(() => {
    // Offers come from the admin catalogue (active services only); keep the static list if the API is unreachable.
    api.publicServices().then((s) => s.length && setServiceOptions(s.map((x) => x.title))).catch(() => {})
  }, [])
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const next: Record<string, string> = {}
    if (form.name.trim().length < 2) next.name = "Indiquez votre nom complet."
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      next.email = "Indiquez une adresse email valide."
    if (form.message.trim().length < 10)
      next.message = "Décrivez votre demande en au moins 10 caractères."
    setErrors(next)
    if (Object.keys(next).length) return
    setLoading(true)
    try {
      setServerError("")
      await api.submitContact({ ...form, website })
      setSent(true)
      setForm({ name: "", email: "", message: "", service: "Demande générale" })
    } catch (err) {
      setSent(false)
      setServerError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }
  return (
    <>
      <Hero
        dark
        eyebrow="CONTACT"
        title="Contactez-nous"
        subtitle="Une équipe à votre écoute pour vos projets technologiques au Mali"
        primary="Nous contacter"
        secondary="Appeler maintenant +223"
        primaryTo="/contact#contact-form"
        secondaryTo="tel:+22320223344"
      />
      <section className="contact-content">
        <div>
          <SectionTitle title="FORMULAIRE DE CONTACT" subtitle="" />
          <form
            className="contact-form"
            id="contact-form"
            onSubmit={submit}
            noValidate
          >
            <label>
              Nom
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Votre nom complet"
              />
              {errors.name && <span>{errors.name}</span>}
            </label>
            <label>
              Email
              <input
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="votre@email.com"
              />
              {errors.email && <span>{errors.email}</span>}
            </label>
            <label>
              Service
              <select
                value={form.service}
                onChange={(e) => setForm({ ...form, service: e.target.value })}
              >
                <option>Demande générale</option>
                {serviceOptions.map((t) => <option key={t}>{t}</option>)}
              </select>
            </label>
            <label>
              Message
              <textarea
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                placeholder="Décrivez votre projet ou votre demande…"
              />
              {errors.message && <span>{errors.message}</span>}
            </label>
            <input tabIndex={-1} autoComplete="off" aria-hidden="true" value={website}
              onChange={(e) => setWebsite(e.target.value)}
              style={{ position: "absolute", left: "-9999px", width: 1, height: 1, opacity: 0 }} name="website" />
            <button className="button primary" disabled={loading}>
              {loading ? (
                "Envoi…"
              ) : (
                <>
                  <Send size={17} /> Envoyer
                </>
              )}
            </button>
            {serverError && <p className="form-error" role="alert">{serverError}</p>}
            {sent && (
              <p className="success">
                <CheckCircle2 /> Merci, votre demande a bien été enregistrée.
              </p>
            )}
          </form>
        </div>
        <div className="contact-side">
          <SectionTitle title="INFOS CONTACT" subtitle="" />
          <div className="contact-info">
            <p>
              <MapPin />
              <b>ADRESSE</b>
              <span>
                Hamdallaye ACI-2000 · Rue 420 Porte 437 · BP 2485 Bamako, Mali
              </span>
            </p>
            <p>
              <Send />
              <b>EMAIL</b>
              <span>dcheick93@hotmail.com</span>
            </p>
            <p>
              <Phone />
              <b>TÉLÉPHONE</b>
              <span>+223 20 22 33 44 / +223 76 54 32 10</span>
            </p>
          </div>
          <SectionTitle title="CARTE – BAMAKO" subtitle="" />
          <img
            className="map"
            src="/assets/bamako-map.jpg"
            alt="Carte de localisation à Bamako, Hamdallaye ACI-2000"
          />
        </div>
      </section>
    </>
  )
}
