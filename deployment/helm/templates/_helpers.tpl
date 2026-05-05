{{/*
Common labels and naming helpers for the isA_user migrations chart.
*/}}

{{- define "migrations.fullname" -}}
{{- if .Values.migrationJob.fullnameOverride -}}
{{- .Values.migrationJob.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-migrate" (.Release.Name | default "isa-user") | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "migrations.labels" -}}
app.kubernetes.io/name: isa-user-migrations
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: migration
app.kubernetes.io/part-of: isa-user
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end -}}

{{- define "migrations.selectorLabels" -}}
app.kubernetes.io/name: isa-user-migrations
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
