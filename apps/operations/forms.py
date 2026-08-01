from django import forms


class SyntheticCustomerRequestForm(forms.Form):
    customer_name = forms.CharField(
        max_length=200,
        label="Synthetic customer name",
        initial="Customer Zero — Founder",
    )
    email = forms.EmailField(
        required=False,
        label="Synthetic email (optional)",
        initial="customer-zero@example.invalid",
    )
    service = forms.ChoiceField(choices=[("establish", "Establish — controlled operating plan")])
    request_text = forms.CharField(
        label="What do you need?",
        widget=forms.Textarea(attrs={"rows": 5}),
        initial="Create a controlled operating plan for my small consultancy.",
    )
    desired_outcome = forms.CharField(
        label="What would a useful result look like?",
        widget=forms.Textarea(attrs={"rows": 3}),
        initial="A clear operating rhythm, priorities, metrics, and authority boundaries.",
    )


class DeliverableReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[("accept", "Accept deliverable"), ("revise", "Request revision")],
        widget=forms.RadioSelect,
    )
    revision_note = forms.CharField(
        required=False,
        label="Revision request",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "revise" and not cleaned.get("revision_note", "").strip():
            self.add_error("revision_note", "Describe the requested revision.")
        return cleaned
