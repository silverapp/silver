For resource definition check out [Resources](Resources#plan) page.

1. [Retrieve all plans](#list-all-plans)
2. [Create a plan](#create-a-plan)
3. [Retrieve a specific plan](#retrieve-a-plan)
4. [Update a plan](#update-a-plan)
5. [Disable a plan](#disable-a-plan)
6. [List all metered features](#list-all-metered-features)
7. [List the metered features of a plan](#list-the-metered-features-of-a-plan)
8. [Create a metered feature](#create-a-metered-feature)

##### List all plans
By default this will list every existing Plan.
```
GET /plans/
```
Filters, such as `enabled` and `private`, can be used for better results. Available filters: `name`, `currency`, `enabled`, `private`, `interval`, `product_code` and `provider`.
```
GET /plans?enabled=True&private=False
```

##### Create a plan
```
POST /plans
```
```json
{
    '<b>name</b>': 'Hydrogen',
    '<b>interval</b>': 'month',
    '<b>interval_count</b>': 1,
    '<b>amount</b>': 150,
    '<b>currency</b>': 'USD',
    'trial_period_days': 15,
    'metered_features': [
        {
            'name': 'Page Views',
            'unit': '100k',
            'price_per_unit': 0.01,
            'included_units': 2.5,
            'product_code': 'existing_pc_2'
        },
        {
            'name': 'VIP Support',
            'price_per_unit': 49.99,
            'included_units': 1,
            'product_code': 'non-existing_pc'
        }
    ],
    'due_days': 10,
    '<b>generate_after</b>': 86400,
    '<b>product_code</b>': 'hyd_3g432556g',
    'enabled': true,
    'private': false,
    '<b>provider</b>': 'www.example.com/providers/2/'
}
```

##### Retrieve a plan
```
GET /plans/:id
```

##### Update a plan
Only `name`, `generate_after` and `due_days` are editable through API.
```
PATCH /plans/:id
```

##### Disable a plan
Plans cannot be actually deleted through API but only through the admin interface. They can be only disabled by API and this is what the `DELETE` verb should do.
```
DELETE /plans/:id
```
##### List all metered features
```
GET /metered-features
```

##### List the metered features of a plan
```
GET /plans/:id/metered-features
```

##### Create a metered feature

```
POST /metered-features/
```
```json
{
  "name": "Random Metered Feature",
  "<b>unit</b>": "pounds",
  "<b>price_per_unit</b>": "100",
  "<b>included_units</b>": "2",
  "<b>product_code</b>": "Code"
}
```
