#!/usr/bin/env bash
# ============================================================
#  Script de test des 7 flux API — EFG Learning
#  Usage : bash test_api.sh
#  Prérequis : curl, jq
#  Le serveur Django doit tourner sur localhost:8000
# ============================================================

BASE="http://localhost:8000/api"
SEP="────────────────────────────────────────"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()    { echo -e "  ${GREEN}✓ $1${NC}"; }
fail()  { echo -e "  ${RED}✗ $1${NC}"; }
info()  { echo -e "  ${YELLOW}→ $1${NC}"; }
title() { echo -e "\n${BLUE}${SEP}${NC}\n${BLUE}  FLUX $1${NC}\n${BLUE}${SEP}${NC}"; }

check_status() {
  local label=$1 expected=$2 actual=$3
  if [ "$actual" = "$expected" ]; then
    ok "$label → HTTP $actual"
  else
    fail "$label → attendu $expected, reçu $actual"
  fi
}

# Extraire depuis réponse paginée ou liste directe
first_id() { echo "$1" | jq -r '(.results[0].id // .[0].id) // empty' 2>/dev/null; }

# ============================================================
# PRÉ-REQUIS : serveur actif + admin créé
# ============================================================
echo -e "\n${BLUE}  Vérification du serveur...${NC}"
PING=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/courses/" 2>/dev/null)
if [ "$PING" != "200" ]; then
  echo -e "${RED}  ✗ Serveur inaccessible sur $BASE (HTTP $PING)${NC}"
  echo "  Lance : python manage.py runserver 0.0.0.0:8000"
  exit 1
fi
ok "Serveur actif"

# Vérifier que jq est installé
if ! command -v jq &>/dev/null; then
  echo -e "${RED}  ✗ jq non installé. Lance : sudo apt install jq${NC}"
  exit 1
fi
ok "jq disponible"

echo ""
echo "  Pour créer le compte admin (une seule fois) :"
echo "  cd \"/home/tiga/Bureau/Dev/e-learning 1.0\" && source env/bin/activate && \\"
echo "  python manage.py shell -c \""
echo "    from apps.users.models import User"
echo "    User.objects.filter(email='admin@efg.com').exists() or \\"
echo "    User.objects.create_user(email='admin@efg.com', password='Admin123!', first_name='Admin', last_name='EFG', role='administrateur', is_staff=True, is_superuser=True)"
echo "  \""

# ============================================================
# FLUX 1 — AUTHENTIFICATION
# ============================================================
title "1 — Authentification"

# 1.1 Inscription apprenant (201=nouveau, 400=déjà existant → on continue)
info "1.1 Inscription apprenant"
REG_A=$(curl -s -w "\n%{http_code}" -X POST "$BASE/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_apprenant@efg.com","first_name":"Test","last_name":"Apprenant","role":"apprenant","password1":"TestPass123!","password2":"TestPass123!"}')
REG_A_STATUS=$(echo "$REG_A" | tail -n 1)
if [ "$REG_A_STATUS" = "201" ]; then
  ok "Inscription apprenant → HTTP 201 (nouveau compte)"
elif [ "$REG_A_STATUS" = "400" ]; then
  ok "Inscription apprenant → HTTP 400 (compte déjà existant, normal)"
else
  fail "Inscription apprenant → HTTP $REG_A_STATUS"
fi

# 1.2 Inscription formateur
info "1.2 Inscription formateur"
REG_F=$(curl -s -w "\n%{http_code}" -X POST "$BASE/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_formateur@efg.com","first_name":"Test","last_name":"Formateur","role":"formateur","password1":"TestPass123!","password2":"TestPass123!"}')
REG_F_STATUS=$(echo "$REG_F" | tail -n 1)
if [ "$REG_F_STATUS" = "201" ]; then
  ok "Inscription formateur → HTTP 201 (nouveau compte)"
elif [ "$REG_F_STATUS" = "400" ]; then
  ok "Inscription formateur → HTTP 400 (compte déjà existant, normal)"
else
  fail "Inscription formateur → HTTP $REG_F_STATUS"
fi

# 1.3 Inscription administrateur doit être bloquée
info "1.3 Inscription avec rôle administrateur (doit être bloquée)"
REG_ADMIN=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{"email":"hacker@efg.com","first_name":"X","last_name":"X","role":"administrateur","password1":"TestPass123!","password2":"TestPass123!"}')
if [ "$REG_ADMIN" = "400" ]; then
  ok "Rôle administrateur bloqué à l'inscription → HTTP 400"
else
  fail "Rôle administrateur NON bloqué → HTTP $REG_ADMIN"
fi

# 1.4 Connexion apprenant
info "1.4 Connexion apprenant"
LOGIN_A=$(curl -s -X POST "$BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_apprenant@efg.com","password":"TestPass123!"}')
ACCESS_TOKEN=$(echo "$LOGIN_A" | jq -r '.tokens.access // .access // empty')
REFRESH_TOKEN=$(echo "$LOGIN_A" | jq -r '.tokens.refresh // .refresh // empty')
if [ -n "$ACCESS_TOKEN" ]; then
  ok "Token apprenant récupéré : ${ACCESS_TOKEN:0:25}..."
else
  fail "Connexion apprenant échouée"
  echo "$LOGIN_A" | jq .
  exit 1
fi

# 1.5 Connexion formateur
info "1.5 Connexion formateur"
LOGIN_F=$(curl -s -X POST "$BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_formateur@efg.com","password":"TestPass123!"}')
ACCESS_FORM=$(echo "$LOGIN_F" | jq -r '.tokens.access // .access // empty')
if [ -n "$ACCESS_FORM" ]; then
  ok "Token formateur récupéré"
else
  fail "Connexion formateur échouée"
fi

# 1.6 Connexion admin
info "1.6 Connexion administrateur"
LOGIN_ADMIN=$(curl -s -X POST "$BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@efg.com","password":"Admin123!"}')
ACCESS_ADMIN=$(echo "$LOGIN_ADMIN" | jq -r '.tokens.access // .access // empty')
if [ -n "$ACCESS_ADMIN" ]; then
  ok "Token admin récupéré"
else
  info "Compte admin@efg.com introuvable (créez-le avec la commande ci-dessus)"
fi

# 1.7 Profil /me/
info "1.7 GET /users/me/"
ME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/users/me/")
check_status "Profil /me/" "200" "$ME_STATUS"

# 1.8 Mise à jour profil (phone + bio)
info "1.8 PATCH /users/me/"
PATCH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/users/me/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"Apprenant","profile":{"phone":"699000000","bio":"Apprenant de test"}}')
check_status "Mise à jour profil" "200" "$PATCH_STATUS"

# 1.9 Refresh token JWT — un seul appel, on récupère le nouveau refresh (rotation)
info "1.9 POST /auth/token/refresh/"
REFRESH_RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/auth/token/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH_TOKEN\"}")
REFRESH_BODY=$(echo "$REFRESH_RESP" | head -n -1)
REFRESH_STATUS=$(echo "$REFRESH_RESP" | tail -n 1)
NEW_REFRESH=$(echo "$REFRESH_BODY" | jq -r '.refresh // empty')
if [ -n "$NEW_REFRESH" ]; then
  REFRESH_TOKEN="$NEW_REFRESH"
fi
check_status "Refresh JWT" "200" "$REFRESH_STATUS"

# ============================================================
# FLUX 2 — CATALOGUE
# ============================================================
title "2 — Catalogue"

# 2.1 Liste des formations (public, sans token)
info "2.1 GET /courses/ (catalogue public)"
CATALOGUE=$(curl -s "$BASE/courses/")
CATALOGUE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/courses/")
check_status "Catalogue public" "200" "$CATALOGUE_STATUS"

NB_FORMATIONS=$(echo "$CATALOGUE" | jq -r '.count // 0')
FORMATION_ID=$(echo "$CATALOGUE" | jq -r '.results[0].id // empty')
info "  Formations disponibles : $NB_FORMATIONS"

if [ -z "$FORMATION_ID" ] || [ "$FORMATION_ID" = "null" ]; then
  fail "Aucune formation — créez-en une via l'admin Django puis relancez"
  FORMATION_ID=1
else
  ok "Formation test ID : $FORMATION_ID"
  # Vérifier les nouveaux champs Flutter (formateur_name, category_name, etc.)
  F_NAME=$(echo "$CATALOGUE" | jq -r '.results[0].formateur_name // "NULL"')
  C_NAME=$(echo "$CATALOGUE" | jq -r '.results[0].category_name // "NULL"')
  L_COUNT=$(echo "$CATALOGUE" | jq -r '.results[0].lessons_count // "NULL"')
  DURATION=$(echo "$CATALOGUE" | jq -r '.results[0].total_duration_minutes // "NULL"')
  IS_FREE=$(echo "$CATALOGUE" | jq -r '.results[0].is_free // "NULL"')
  if [ "$F_NAME" != "NULL" ] && [ "$C_NAME" != "NULL" ]; then
    ok "Champs Flutter présents : formateur_name, category_name, lessons_count, total_duration_minutes"
  else
    fail "Champs Flutter manquants → formateur_name=$F_NAME | category_name=$C_NAME"
  fi
  info "  formateur_name=$F_NAME | category_name=$C_NAME | lessons_count=$L_COUNT | duration=${DURATION}min | is_free=$IS_FREE"
fi

# 2.2 Recherche
info "2.2 GET /courses/?search=..."
SEARCH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/courses/?search=formation")
check_status "Recherche" "200" "$SEARCH_STATUS"

# 2.3 Filtre par niveau
info "2.3 GET /courses/?niveau=debutant"
FILTER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/courses/?niveau=debutant")
check_status "Filtre par niveau" "200" "$FILTER_STATUS"

# 2.4 Détail formation (vérifie formateur_name + category_name plats)
info "2.4 GET /courses/$FORMATION_ID/"
DETAIL=$(curl -s "$BASE/courses/$FORMATION_ID/")
DETAIL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/courses/$FORMATION_ID/")
check_status "Détail formation" "200" "$DETAIL_STATUS"
D_FNAME=$(echo "$DETAIL" | jq -r '.formateur_name // "NULL"')
D_CNAME=$(echo "$DETAIL" | jq -r '.category_name // "NULL"')
D_MOD=$(echo "$DETAIL" | jq -r '.modules_count // "NULL"')
D_LES=$(echo "$DETAIL" | jq -r '.lessons_count // "NULL"')
info "  formateur_name=$D_FNAME | category_name=$D_CNAME | modules_count=$D_MOD | lessons_count=$D_LES"

# 2.5 Catégories
info "2.5 GET /courses/categories/"
CAT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/courses/categories/")
check_status "Liste catégories" "200" "$CAT_STATUS"

# ============================================================
# FLUX 3 — INSCRIPTION
# ============================================================
title "3 — Inscription"

# 3.1 Liste mes inscriptions
info "3.1 GET /enrollments/"
ENROLL_LIST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/enrollments/")
check_status "Liste inscriptions" "200" "$ENROLL_LIST_STATUS"

# 3.2 Inscription (formation_id — champ corrigé)
info "3.2 POST /enrollments/ avec formation_id=$FORMATION_ID"
ENROLL=$(curl -s -w "\n%{http_code}" -X POST "$BASE/enrollments/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"formation_id\":$FORMATION_ID}")
ENROLL_BODY=$(echo "$ENROLL" | head -n -1)
ENROLL_STATUS=$(echo "$ENROLL" | tail -n 1)

if [ "$ENROLL_STATUS" = "201" ]; then
  ok "Inscription créée → HTTP 201"
  ENROLLMENT_ID=$(echo "$ENROLL_BODY" | jq -r '.id // empty')
  ENROLL_STATUS_FIELD=$(echo "$ENROLL_BODY" | jq -r '.status // empty')
  info "  enrollment_id=$ENROLLMENT_ID | status=$ENROLL_STATUS_FIELD"
elif [ "$ENROLL_STATUS" = "400" ]; then
  MSG=$(echo "$ENROLL_BODY" | jq -r '.detail // .non_field_errors[0] // .formation_id[0] // "voir détail"' 2>/dev/null)
  ok "HTTP 400 → $MSG (déjà inscrit ou formation payante)"
  ENROLLMENT_ID=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/enrollments/" \
    | jq -r ".results[] | select(.formation == $FORMATION_ID) | .id" | head -1)
else
  fail "Inscription → HTTP $ENROLL_STATUS"
  echo "$ENROLL_BODY" | jq . 2>/dev/null | head -5
  ENROLLMENT_ID=1
fi

# 3.3 Double inscription bloquée
info "3.3 Double inscription (doit retourner 400)"
DOUBLE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/enrollments/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"formation_id\":$FORMATION_ID}")
if [ "$DOUBLE" = "400" ]; then
  ok "Double inscription bloquée → HTTP 400"
else
  info "Double inscription → HTTP $DOUBLE"
fi

# ============================================================
# FLUX 4 — PROGRESSION
# ============================================================
title "4 — Progression"

# Récupérer module et leçon depuis la formation
info "4.0 Récupération des modules de la formation $FORMATION_ID"
MODULES_RESP=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE/courses/$FORMATION_ID/modules/")

# Gère réponse paginée {results:[...]} ET liste directe [...]
MODULE_ID=$(echo "$MODULES_RESP" | jq -r '(.results // .) | .[0].id // empty' 2>/dev/null)
LESSON_ID=$(echo "$MODULES_RESP" | jq -r '(.results // .) | .[0].lessons[0].id // empty' 2>/dev/null)

if [ -n "$MODULE_ID" ] && [ "$MODULE_ID" != "null" ]; then
  info "  module_id=$MODULE_ID | lesson_id=${LESSON_ID:-aucune}"
else
  info "  Aucun module — créez-en un via l'admin"
fi

# 4.1 Liste progressions
info "4.1 GET /progress/formations/"
check_status "Liste progressions" "200" \
  "$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/progress/formations/")"

# 4.2 Progression par formation
info "4.2 GET /progress/formations/$FORMATION_ID/"
PROG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/progress/formations/$FORMATION_ID/")
if [ "$PROG_STATUS" = "200" ]; then
  ok "Progression formation → HTTP 200"
elif [ "$PROG_STATUS" = "404" ]; then
  info "Progression formation → HTTP 404 (pas encore de progression)"
else
  fail "Progression formation → HTTP $PROG_STATUS"
fi

# 4.3 Marquer leçon terminée
if [ -n "$LESSON_ID" ] && [ "$LESSON_ID" != "null" ]; then
  info "4.3 POST /progress/lessons/$LESSON_ID/complete/"
  COMPLETE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "$BASE/progress/lessons/$LESSON_ID/complete/")
  if [ "$COMPLETE" = "200" ] || [ "$COMPLETE" = "201" ]; then
    ok "Leçon marquée terminée → HTTP $COMPLETE"
  else
    fail "Marquer leçon → HTTP $COMPLETE"
  fi

  # 4.4 Sauvegarder position vidéo
  info "4.4 POST /progress/lessons/$LESSON_ID/video/"
  VIDEO=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"position_seconds":120}' \
    "$BASE/progress/lessons/$LESSON_ID/video/")
  if [ "$VIDEO" = "200" ] || [ "$VIDEO" = "201" ]; then
    ok "Position vidéo sauvegardée → HTTP $VIDEO"
  else
    fail "Position vidéo → HTTP $VIDEO"
  fi
else
  info "Pas de leçon disponible — ajoutez-en une via l'admin"
fi

# 4.5 Reprendre la formation (retourne lesson_id)
info "4.5 GET /progress/formations/$FORMATION_ID/resume/"
RESUME=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/progress/formations/$FORMATION_ID/resume/")
RESUME_STATUS=$(echo "$RESUME" | tail -n 1)
RESUME_BODY=$(echo "$RESUME" | head -n -1)
if [ "$RESUME_STATUS" = "200" ]; then
  LESSON_ID_RESUME=$(echo "$RESUME_BODY" | jq -r '.lesson_id // "null"')
  ok "Reprise → HTTP 200 | lesson_id=$LESSON_ID_RESUME"
elif [ "$RESUME_STATUS" = "404" ]; then
  info "Reprise → HTTP 404 (pas encore de progression enregistrée)"
else
  fail "Reprise → HTTP $RESUME_STATUS"
fi

# ============================================================
# FLUX 5 — QUIZ
# ============================================================
title "5 — Quiz"

if [ -n "$MODULE_ID" ] && [ "$MODULE_ID" != "null" ]; then
  info "5.1 GET /quizzes/modules/$MODULE_ID/quiz/"
  QUIZ=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/quizzes/modules/$MODULE_ID/quiz/")
  QUIZ_BODY=$(echo "$QUIZ" | head -n -1)
  QUIZ_STATUS=$(echo "$QUIZ" | tail -n 1)

  if [ "$QUIZ_STATUS" = "200" ]; then
    ok "Quiz récupéré → HTTP 200"
    QUIZ_ID=$(echo "$QUIZ_BODY" | jq -r '.id // empty')
    NB_Q=$(echo "$QUIZ_BODY" | jq -r '.questions | length')
    info "  quiz_id=$QUIZ_ID | questions=$NB_Q"

    if [ -n "$QUIZ_ID" ] && [ "$NB_Q" -gt "0" ] 2>/dev/null; then
      # 5.2 Soumission (première réponse de chaque question)
      info "5.2 POST /quizzes/$QUIZ_ID/submit/"
      ANSWERS=$(echo "$QUIZ_BODY" | jq '[.questions[] | {question_id: .id, answer_id: (.answers[0].id // 0)}]')
      SUBMIT=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"answers\":$ANSWERS}" \
        "$BASE/quizzes/$QUIZ_ID/submit/")
      SUBMIT_BODY=$(echo "$SUBMIT" | head -n -1)
      SUBMIT_STATUS=$(echo "$SUBMIT" | tail -n 1)
      check_status "Soumission quiz" "201" "$SUBMIT_STATUS"

      if [ "$SUBMIT_STATUS" = "201" ]; then
        SCORE=$(echo "$SUBMIT_BODY" | jq -r '.score // "?"')
        PASSED=$(echo "$SUBMIT_BODY" | jq -r '.passed // "?"')
        COMPLETED_AT=$(echo "$SUBMIT_BODY" | jq -r '.completed_at // "MANQUANT"')
        info "  score=${SCORE}% | passed=$PASSED | completed_at=$COMPLETED_AT"
        if [ "$COMPLETED_AT" != "MANQUANT" ] && [ "$COMPLETED_AT" != "null" ]; then
          ok "Champ completed_at présent (Flutter lit ce champ)"
        else
          fail "completed_at manquant dans la réponse"
        fi
      fi

      # 5.3 Historique
      info "5.3 GET /quizzes/$QUIZ_ID/history/"
      check_status "Historique quiz" "200" \
        "$(curl -s -o /dev/null -w "%{http_code}" \
          -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/quizzes/$QUIZ_ID/history/")"
    else
      info "Quiz sans questions — ajoutez-en via l'admin"
    fi
  elif [ "$QUIZ_STATUS" = "404" ]; then
    info "Pas de quiz pour ce module → HTTP 404 (créez-en un via l'admin)"
  else
    fail "Quiz → HTTP $QUIZ_STATUS"
  fi
else
  info "Pas de module — créez la structure (module + leçon + quiz) via l'admin"
fi

# ============================================================
# FLUX 6 — CERTIFICATS
# ============================================================
title "6 — Certificats"

# 6.1 Liste
info "6.1 GET /certificates/"
CERT_LIST=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/certificates/")
CERT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/certificates/")
check_status "Liste certificats" "200" "$CERT_STATUS"

CERT_COUNT=$(echo "$CERT_LIST" | jq -r '.count // 0')
info "  Certificats obtenus : $CERT_COUNT"

CERT_ID=$(echo "$CERT_LIST" | jq -r '.results[0].id // empty')
CERT_CODE=$(echo "$CERT_LIST" | jq -r '.results[0].verification_code // empty')

if [ -n "$CERT_ID" ] && [ "$CERT_ID" != "null" ]; then
  # Vérifier le champ formation_titre (clé corrigée)
  CERT_TITRE=$(echo "$CERT_LIST" | jq -r '.results[0].formation_titre // "MANQUANT"')
  if [ "$CERT_TITRE" != "MANQUANT" ] && [ "$CERT_TITRE" != "null" ]; then
    ok "Champ formation_titre présent : $CERT_TITRE"
  else
    fail "formation_titre manquant (Flutter lit ce champ)"
  fi

  # 6.2 Téléchargement PDF
  info "6.2 GET /certificates/$CERT_ID/download/"
  DL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/certificates/$CERT_ID/download/")
  if [ "$DL_STATUS" = "200" ]; then
    ok "Téléchargement PDF → HTTP 200"
  else
    info "PDF → HTTP $DL_STATUS (404 = pdf_file non généré)"
  fi

  # 6.3 Vérification par code
  if [ -n "$CERT_CODE" ] && [ "$CERT_CODE" != "null" ]; then
    info "6.3 GET /certificates/verify/$CERT_CODE/"
    VERIFY=$(curl -s "$BASE/certificates/verify/$CERT_CODE/")
    VERIFY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      "$BASE/certificates/verify/$CERT_CODE/")
    check_status "Vérification certificat" "200" "$VERIFY_STATUS"
    IS_VALID=$(echo "$VERIFY" | jq -r '.is_valid // "?"')
    info "  is_valid=$IS_VALID"
  fi
else
  info "Aucun certificat — complétez une formation à 100% pour en générer un automatiquement"
fi

# 6.4 Faux code (is_valid=false)
info "6.4 GET /certificates/verify/FAUX-CODE-123/ (faux code)"
FAKE=$(curl -s "$BASE/certificates/verify/FAUX-CODE-123/")
FAKE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/certificates/verify/FAUX-CODE-123/")
IS_VALID_FAKE=$(echo "$FAKE" | jq -r '.is_valid // "?"')
if [ "$FAKE_STATUS" = "200" ] && [ "$IS_VALID_FAKE" = "false" ]; then
  ok "Faux code → HTTP 200 | is_valid=false"
else
  info "Faux code → HTTP $FAKE_STATUS | is_valid=$IS_VALID_FAKE"
fi

# ============================================================
# FLUX 7 — DASHBOARD
# ============================================================
title "7 — Dashboard"

# 7.1 Dashboard apprenant
info "7.1 GET /dashboard/student/"
STUDENT_DASH=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/dashboard/student/")
STUDENT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE/dashboard/student/")
check_status "Dashboard apprenant" "200" "$STUDENT_STATUS"

if [ "$STUDENT_STATUS" = "200" ]; then
  FEC=$(echo "$STUDENT_DASH" | jq -r '.formations_en_cours // "MANQUANT"')
  FTE=$(echo "$STUDENT_DASH" | jq -r '.formations_terminees // "MANQUANT"')
  QP=$(echo "$STUDENT_DASH"  | jq -r '.quiz_passes // "MANQUANT"')
  CO=$(echo "$STUDENT_DASH"  | jq -r '.certificats_obtenus // "MANQUANT"')
  info "  formations_en_cours=$FEC | formations_terminees=$FTE | quiz_passes=$QP | certificats_obtenus=$CO"
  if [ "$FEC" != "MANQUANT" ] && [ "$QP" != "MANQUANT" ]; then
    ok "Toutes les clés Flutter du dashboard apprenant présentes"
  else
    fail "Clés manquantes dans le dashboard apprenant"
  fi
fi

# 7.2 Dashboard formateur
if [ -n "$ACCESS_FORM" ]; then
  info "7.2 GET /dashboard/formateur/"
  FORM_DASH=$(curl -s -H "Authorization: Bearer $ACCESS_FORM" "$BASE/dashboard/formateur/")
  FORM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_FORM" "$BASE/dashboard/formateur/")
  check_status "Dashboard formateur" "200" "$FORM_STATUS"

  if [ "$FORM_STATUS" = "200" ]; then
    TF=$(echo "$FORM_DASH"  | jq -r '.total_formations // "MANQUANT"')
    TA=$(echo "$FORM_DASH"  | jq -r '.total_apprenants // "MANQUANT"')
    TR=$(echo "$FORM_DASH"  | jq -r '.total_revenus // "MANQUANT"')
    TC=$(echo "$FORM_DASH"  | jq -r '.taux_completion // "MANQUANT"')
    NF=$(echo "$FORM_DASH"  | jq -r '.formations | length // "MANQUANT"')
    info "  total_formations=$TF | total_apprenants=$TA | total_revenus=$TR | taux_completion=$TC% | formations=$NF"
    if [ "$TA" != "MANQUANT" ] && [ "$TR" != "MANQUANT" ] && [ "$TC" != "MANQUANT" ]; then
      ok "Toutes les clés Flutter du dashboard formateur présentes"
    else
      fail "Clés manquantes dans le dashboard formateur"
    fi
  fi
fi

# 7.3 Dashboard admin
if [ -n "$ACCESS_ADMIN" ]; then
  info "7.3 GET /dashboard/admin/"
  ADMIN_DASH=$(curl -s -H "Authorization: Bearer $ACCESS_ADMIN" "$BASE/dashboard/admin/")
  ADMIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ACCESS_ADMIN" "$BASE/dashboard/admin/")
  check_status "Dashboard admin" "200" "$ADMIN_STATUS"

  if [ "$ADMIN_STATUS" = "200" ]; then
    TU=$(echo "$ADMIN_DASH" | jq -r '.total_users // "MANQUANT"')
    TFO=$(echo "$ADMIN_DASH" | jq -r '.total_formations // "MANQUANT"')
    TE=$(echo "$ADMIN_DASH"  | jq -r '.total_enrollments // "MANQUANT"')
    TRE=$(echo "$ADMIN_DASH" | jq -r '.total_revenus // "MANQUANT"')
    NRE=$(echo "$ADMIN_DASH" | jq -r '.recent_enrollments | length // "MANQUANT"')
    info "  total_users=$TU | total_formations=$TFO | total_enrollments=$TE | total_revenus=$TRE | recent_enrollments=$NRE"
    if [ "$TRE" != "MANQUANT" ] && [ "$NRE" != "MANQUANT" ]; then
      ok "Toutes les clés Flutter du dashboard admin présentes"
    else
      fail "Clés manquantes dans le dashboard admin"
    fi
  fi
else
  info "Dashboard admin ignoré (pas de compte admin — voir commande en haut)"
fi

# ============================================================
# LOGOUT
# ============================================================
echo ""
info "Déconnexion apprenant..."
LOGOUT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/logout/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH_TOKEN\"}")
# simplejwt retourne 205 (No Content) pour le logout
if [ "$LOGOUT" = "200" ] || [ "$LOGOUT" = "205" ]; then
  ok "Logout → HTTP $LOGOUT"
else
  fail "Logout → attendu 200 ou 205, reçu $LOGOUT"
fi

# ============================================================
# RÉSUMÉ
# ============================================================
echo -e "\n${BLUE}${SEP}${NC}"
echo -e "${BLUE}  FIN DES TESTS${NC}"
echo -e "${BLUE}${SEP}${NC}"
echo ""
echo "  Téléphone physique → remplace BASE par :"
echo "    BASE=\"http://192.168.0.113:8000/api\""
echo ""
