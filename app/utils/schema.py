"""Single source of truth for the model's input features.

The model reads all 20 attributes of the credit dataset. Text values are
replaced by integer codes before they reach it; ordered values (balances,
length of employment) are coded in their natural order. Forms, the JSON API,
CSV uploads and the training script all take the feature order, labels,
ranges and codes from here, so they cannot drift apart.

The dataset is a copy of the Statlog (German Credit) data with renamed
columns. Labels follow the column names of this copy.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Choice:
    code: int    # value the model is trained on
    raw: str     # value as written in the dataset CSV
    label: str   # wording shown in the interface


@dataclass(frozen=True)
class Feature:
    name: str
    label: str
    kind: str                          # 'number' or 'choice'
    help: str = ''
    unit: str = ''
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    integer: bool = False
    widget: str = 'select'             # 'select' or 'segmented' (choice fields)
    choices: Tuple[Choice, ...] = ()

    def choice_for(self, code: int) -> Optional[Choice]:
        for choice in self.choices:
            if choice.code == code:
                return choice
        return None


def _choices(*pairs: Tuple[str, str]) -> Tuple[Choice, ...]:
    """Number the choices 1..n in the order they are listed."""
    return tuple(Choice(code, raw, label) for code, (raw, label) in enumerate(pairs, start=1))


def _scale(top: int) -> Tuple[Choice, ...]:
    """A 1..n scale that the dataset already stores as numbers."""
    return tuple(Choice(value, str(value), str(value)) for value in range(1, top + 1))


# Order matters: this is the dataset's column order and the order the model is fitted on.
FEATURES: Tuple[Feature, ...] = (
    Feature(
        name='over_draft', label='Checking account', kind='choice',
        help='Balance of the checking account.',
        choices=_choices(
            ('<0', 'Overdrawn'),
            ('0<=X<200', 'Under 200'),
            ('>=200', '200 or more'),
            ('no checking', 'No checking account'),
        ),
    ),
    Feature(
        name='credit_usage', label='Credit usage', kind='number',
        help='How long the credit runs. The dataset spans 4 to 72 months.',
        unit='months', minimum=1, maximum=120, integer=True,
    ),
    Feature(
        name='credit_history', label='Credit history', kind='choice',
        choices=_choices(
            ('no credits/all paid', 'No credit taken, or all paid back'),
            ('all paid', 'All credit at this bank paid back'),
            ('existing paid', 'Existing credit paid back so far'),
            ('delayed previously', 'Delays in paying in the past'),
            ('critical/other existing credit', 'Critical account, or credit elsewhere'),
        ),
    ),
    Feature(
        name='purpose', label='Purpose', kind='choice',
        choices=_choices(
            ('new car', 'New car'),
            ('used car', 'Used car'),
            ('furniture/equipment', 'Furniture or equipment'),
            ('radio/tv', 'Radio or TV'),
            ('domestic appliance', 'Domestic appliance'),
            ('repairs', 'Repairs'),
            ('education', 'Education'),
            ('retraining', 'Retraining'),
            ('business', 'Business'),
            ('other', 'Other'),
        ),
    ),
    Feature(
        name='current_balance', label='Current balance', kind='number',
        help='Amount of credit. The dataset spans 250 to 18,424.',
        minimum=0, maximum=1_000_000,
    ),
    Feature(
        name='average_credit_balance', label='Savings balance', kind='choice',
        help='Average balance held in savings.',
        choices=_choices(
            ('no known savings', 'No known savings'),
            ('<100', 'Under 100'),
            ('100<=X<500', '100 to 499'),
            ('500<=X<1000', '500 to 999'),
            ('>=1000', '1,000 or more'),
        ),
    ),
    Feature(
        name='employment', label='Employment', kind='choice',
        help='Time in the current job.',
        choices=_choices(
            ('unemployed', 'Unemployed'),
            ('<1', 'Under 1 year'),
            ('1<=X<4', '1 to 3 years'),
            ('4<=X<7', '4 to 6 years'),
            ('>=7', '7 years or more'),
        ),
    ),
    Feature(
        name='location', label='Location', kind='choice', widget='segmented',
        help='A scale of 1 to 4, as coded in the dataset.',
        choices=_scale(4),
    ),
    Feature(
        name='personal_status', label='Personal status', kind='choice',
        choices=_choices(
            ('male single', 'Male, single'),
            ('male mar/wid', 'Male, married or widowed'),
            ('male div/sep', 'Male, divorced or separated'),
            ('female div/dep/mar', 'Female, divorced, separated or married'),
        ),
    ),
    Feature(
        name='other_parties', label='Other parties', kind='choice', widget='segmented',
        help='Anyone else liable for the credit.',
        choices=_choices(
            ('none', 'None'),
            ('co applicant', 'Co-applicant'),
            ('guarantor', 'Guarantor'),
        ),
    ),
    Feature(
        name='residence_since', label='Residence since', kind='choice', widget='segmented',
        help='Time at the current address, on the dataset\'s scale of 1 to 4.',
        choices=_scale(4),
    ),
    Feature(
        name='property_magnitude', label='Property', kind='choice',
        help='Most valuable asset on record.',
        choices=_choices(
            ('real estate', 'Real estate'),
            ('life insurance', 'Life insurance'),
            ('car', 'Car'),
            ('no known property', 'No known property'),
        ),
    ),
    Feature(
        name='cc_age', label='Age', kind='number',
        help='Age of the applicant. The dataset spans 19 to 75.',
        unit='years', minimum=18, maximum=100, integer=True,
    ),
    Feature(
        name='other_payment_plans', label='Other payment plans', kind='choice', widget='segmented',
        help='Instalment plans running elsewhere.',
        choices=_choices(
            ('none', 'None'),
            ('bank', 'Bank'),
            ('stores', 'Stores'),
        ),
    ),
    Feature(
        name='housing', label='Housing', kind='choice', widget='segmented',
        choices=_choices(
            ('own', 'Own'),
            ('rent', 'Rent'),
            ('for free', 'Rent-free'),
        ),
    ),
    Feature(
        name='existing_credits', label='Existing credits', kind='choice', widget='segmented',
        help='Credits already held at this bank.',
        choices=_scale(4),
    ),
    Feature(
        name='job', label='Job', kind='choice',
        choices=_choices(
            ('unemp/unskilled non res', 'Unemployed or unskilled, non-resident'),
            ('unskilled resident', 'Unskilled, resident'),
            ('skilled', 'Skilled'),
            ('high qualif/self emp/mgmt', 'Highly qualified, self-employed or management'),
        ),
    ),
    Feature(
        name='num_dependents', label='Dependents', kind='choice', widget='segmented',
        help='People the applicant supports.',
        choices=_scale(2),
    ),
    Feature(
        name='own_telephone', label='Telephone', kind='choice', widget='segmented',
        help='A telephone registered in the applicant\'s name.',
        choices=_choices(
            ('yes', 'Yes'),
            ('none', 'No'),
        ),
    ),
    Feature(
        name='foreign_worker', label='Foreign worker', kind='choice', widget='segmented',
        choices=_choices(
            ('yes', 'Yes'),
            ('no', 'No'),
        ),
    ),
)

FEATURE_NAMES: Tuple[str, ...] = tuple(feature.name for feature in FEATURES)
FEATURES_BY_NAME: Dict[str, Feature] = {feature.name: feature for feature in FEATURES}

# How the form groups the inputs: (key, title, description, feature names in reading order).
GROUPS: Tuple[Tuple[str, str, str, Tuple[str, ...]], ...] = (
    ('credit', 'The credit', 'What is being asked for, and on what terms.',
     ('purpose', 'current_balance', 'credit_usage', 'location', 'other_parties', 'other_payment_plans')),
    ('history', 'Accounts and history', 'How the applicant has handled money so far.',
     ('over_draft', 'average_credit_balance', 'credit_history', 'property_magnitude', 'existing_credits')),
    ('applicant', 'The applicant', 'Who is asking.',
     ('cc_age', 'personal_status', 'job', 'employment', 'housing', 'residence_since',
      'num_dependents', 'own_telephone', 'foreign_worker')),
)

# Target column of the dataset. "bad" is the class the model is looking for.
TARGET_COLUMN = 'class'
TARGET_CODES: Dict[str, int] = {'good': 0, 'bad': 1}
TARGET_LABELS: Dict[int, str] = {0: 'good', 1: 'bad'}


def features_in_group(group: str) -> Tuple[Feature, ...]:
    for key, _, _, names in GROUPS:
        if key == group:
            return tuple(FEATURES_BY_NAME[name] for name in names)
    return ()


def describe_features() -> Dict[str, dict]:
    """Machine-readable description of every input, for the JSON API."""
    described = {}
    for feature in FEATURES:
        entry = {'label': feature.label, 'type': feature.kind}
        if feature.help:
            entry['help'] = feature.help
        if feature.kind == 'number':
            entry['minimum'] = feature.minimum
            entry['maximum'] = feature.maximum
            if feature.unit:
                entry['unit'] = feature.unit
        else:
            entry['choices'] = [
                {'code': choice.code, 'value': choice.raw, 'label': choice.label}
                for choice in feature.choices
            ]
        described[feature.name] = entry
    return described
