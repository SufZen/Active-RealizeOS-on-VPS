# Known Contacts — Portuguese Entities

Contact directory for common Portuguese government bodies, utilities, and services.
Used by the `contact` skill to look up phone numbers, channels, and operating notes.

---

## Government / Tax

```yaml
financas_at_general:
  name: "Finanças / AT — General Line"
  phone: "+351 217 206 707"
  channels: [phone]
  hours: "Mon–Fri 9:00–19:00"
  language: pt
  ivr_notes: "Say your NIF when prompted. For IRS: option 2. For debt: option for 'Dívidas'. For certificates: say 'certidões'."
  notes: "Long wait times; call before 10:00 or after 16:00 for faster service."

financas_setubal:
  name: "Serviço de Finanças de Setúbal"
  phone: "+351 265 xxx xxx"
  website: "portaldasfinancas.gov.pt"
  channels: [phone, in_person]
  hours: "Mon–Fri 9:00–16:30"
  language: pt
  notes: "Check current address and phone at portaldasfinancas.gov.pt > Localizar > Setúbal."

seguranca_social:
  name: "Segurança Social — Employer Line"
  phone: "300 502 502"
  channels: [phone]
  hours: "Mon–Fri 9:00–18:00"
  language: pt
  ivr_notes: "Select option for 'Empregadores' for HomeAid SS matters."

seguranca_social_setubal:
  name: "Centro Distrital SS Setúbal"
  phone: "+351 265 541 100"
  channels: [phone, in_person]
  hours: "Mon–Fri 9:00–16:30"
  language: pt
  address: "Av. Luísa Todi, 72, 2900 Setúbal (confirm at seg-social.pt)"

irn_loja_cidadao:
  name: "Loja do Cidadão Setúbal (IRN, CC, Civil Registry)"
  phone: "+351 210 107 600"
  channels: [phone, in_person]
  hours: "Check portaldocidadao.pt for current hours"
  language: pt
  address: "Av. Luísa Todi, Setúbal"
  booking: "agendamento.irn.mj.pt"
```

## Municipal / Câmara

```yaml
camara_setubal:
  name: "Câmara Municipal de Setúbal — General"
  phone: "+351 265 541 000"
  website: "setubal.pt"
  channels: [phone, email, in_person]
  email: "geral@mun-setubal.pt"
  hours: "Mon–Fri 9:00–17:00"
  language: pt

camara_setubal_urbanismo:
  name: "Câmara Setúbal — Urbanismo / Obras"
  phone: "+351 265 541 000"
  channels: [phone, in_person]
  hours: "Mon–Fri 9:00–17:00"
  language: pt
  ivr_notes: "Ask for 'Departamento de Urbanismo' or 'Obras Particulares'."
  notes: "For permits and planning: bring all documents; appointments improve service."
```

## Healthcare

```yaml
centro_saude_setubal:
  name: "Centro de Saúde de Setúbal"
  phone: "+351 265 549 200"
  channels: [phone]
  hours: "Mon–Fri 8:00–20:00"
  language: pt
  ivr_notes: "For appointment: press 1. For nurse line: press 2."
  notes: "Book via SNS 24 online first; call if online not available."

sns24:
  name: "SNS 24 — Health Helpline"
  phone: "808 24 24 24"
  channels: [phone]
  hours: "24/7"
  language: pt
  notes: "Triage line. Redirects to nearest emergency if needed. Also books appointments."
```

## Utilities

```yaml
edp_residential:
  name: "EDP — Residential Customer Line"
  phone: "800 500 900"
  channels: [phone]
  hours: "Mon–Fri 9:00–21:00, Sat 9:00–17:00"
  language: pt
  ivr_notes: "For transfers/changes: option for 'Mudar Titular'. For billing: option for 'Faturação'."
  notes: "Free phone number. Best to have CPE meter code before calling."

smas_setubal:
  name: "SMAS Setúbal — Water & Sanitation"
  phone: "+351 265 549 100"
  channels: [phone, email, in_person]
  email: "smas@smas.setubal.pt"
  hours: "Mon–Fri 8:30–17:00"
  language: pt
  notes: "Water transfers require in-person visit or email with signed form + escritura."
```

## Telecom

```yaml
digi_portugal:
  name: "DIGI Portugal — Customer Service"
  phone: "+351 923 30 90 30"
  website: "digi.pt/area-cliente"
  channels: [phone]
  hours: "Mon–Sun 8:00–22:00"
  language: pt
  ivr_notes: "Press 1 for billing, 2 for technical support. For cancellations ask for 'departamento de cancelamentos'."
  notes: "Asaf has 5 lines on his account. NIF required for verification. They may offer retention deals — decline if Asaf wants to cancel."

nos_portugal:
  name: "NOS — Customer Service"
  phone: "+351 16990"
  channels: [phone]
  hours: "Mon–Sun 8:00–22:00"
  language: pt
  ivr_notes: "Press 2 for mobile, 3 for fixed services."

meo_portugal:
  name: "MEO — Customer Service"
  phone: "+351 16200"
  channels: [phone]
  hours: "Mon–Sun 8:00–22:00"
  language: pt

vodafone_portugal:
  name: "Vodafone — Customer Service"
  phone: "+351 16912"
  channels: [phone]
  hours: "Mon–Sun 8:00–22:00"
  language: pt
```

## Banking

```yaml
bank_general:
  name: "Your Main Bank — 24h Line"
  channels: [phone]
  notes: "Check the back of your bank card or your bank app for the 24h support number."
```

## Emergency / Essential

```yaml
inem:
  name: "INEM — Medical Emergency"
  phone: "112"
  channels: [phone]
  hours: "24/7"
  language: pt

psp_setubal:
  name: "PSP Setúbal — Police"
  phone: "+351 265 522 022"
  channels: [phone]
  hours: "24/7"
  language: pt
```
