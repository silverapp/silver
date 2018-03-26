---
title: Silver API
description: Here is an overview of the Silver API. You can find useful information about how to paginate the results and iterate through the entire collection.
---
General API specification.

##### Listing

Requests that return multiple items are paginated by default to 30 items. You can specify the `page` parameter for the page number and `per_page` to increase/decrease the items per page. There is a hard limit of items per page of `100`. The page numbering is 1-based and if you do not specify a `page` parameter it's default value is 1.

__NOTE__ that not all listings can be iterated using `page` parameters and some ignore the page parameter.

##### Iterating entire collection

In order to iterate the entire collection you must follow the `Link` header.
```
Link: <https://api.example.com/silver/subscriptions?page=3&per_page=100>; rel="next",
  <https://api.example.com/silver/subscriptions?page=last&per_page=100>; rel="last"
```

The possible `rel` values are:

| Name	| Description                                                |
|-------|------------------------------------------------------------|
| next	| Shows the URL of the immediate next page of results.       |
| last	| Shows the URL of the last page of results.                 |
| first	| Shows the URL of the first page of results.                |
| prev	| Shows the URL of the immediate previous page of results.   |
