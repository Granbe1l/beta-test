# Actual UI capture checklist — reviewer release gate

Screenshots in `docs/gallery/` are browser captures, not product mockups.
To keep the compact preview representative, the CI screenshot collector
resets the internal Streamlit page scroll to the top and moves the mouse
away from hover tooltips before taking each of the six desktop previews.

On the initial Dashboard view, **What should we inspect?** and the original
source action now render before the optional activity/repository filters.
The lead summary still uses the actual selected verified cohort and retains
its 28-day coverage count, the separate complete open-Issue-inventory
indicator and the seven-day observation disclaimer.

Required release checks: real snapshot; zero visible Streamlit exceptions;
six mobile pages without horizontal overflow; all evidence CTA links valid;
source/status flags unchanged; actual screenshot CI passing. Changing CSS
alone is not evidence of a human comprehension improvement. No fabricated
HR survey scores are permitted.
