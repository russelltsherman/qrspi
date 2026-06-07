# JMESPath & `--query` Reference

The AWS CLI evaluates `--query` with [JMESPath](https://jmespath.org). It runs
**client-side**, after the API response returns — it does not reduce what the API
sends. Use it to shape, filter, and project output. Pair it with `--output text`
for shell pipelines and `--output table` for human inspection.

All examples use placeholder tokens (`<bucket>`, `i-xxx`, `<arn>`, `<name>`).

## Field selection & projection

Select a single scalar:

```bash
aws ec2 describe-instances \
  --query 'Reservations[0].Instances[0].InstanceId' --output text
```

Project a field across a list (the `[]` flattens nested lists):

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].InstanceId' --output text
```

Multi-select hash — reshape each element into a new object with renamed keys
(ideal for `--output table`):

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].{ID:InstanceId,Type:InstanceType,State:State.Name}' \
  --output table
```

Multi-select list — fixed column order for `--output text` (text output orders
columns by the list order, NOT alphabetically — see below):

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name]' \
  --output text
```

## List & map filters

Filter expression `[?<predicate>]`. String literals use **backtick** or single
quotes inside the JMESPath, with the whole expression single-quoted for the shell:

```bash
# Instances of a given type
aws ec2 describe-instances \
  --query "Reservations[].Instances[?InstanceType=='t3.micro'].InstanceId" \
  --output text

# Running instances only
aws ec2 describe-instances \
  --query "Reservations[].Instances[?State.Name=='running'].InstanceId" \
  --output text
```

Numeric comparison, negation, and boolean combinators (`&&`, `||`, `!`):

```bash
aws ec2 describe-volumes \
  --query "Volumes[?Size > `100` && State=='available'].VolumeId" \
  --output text
```

Filter on a tag (tags are a list of `{Key,Value}` — use `contains` /
nested filter):

```bash
aws ec2 describe-instances \
  --query "Reservations[].Instances[?Tags[?Key=='Name' && Value=='<name>']].InstanceId" \
  --output text
```

Functions: `contains(@, 'x')`, `starts_with(Name, '<prefix>')`,
`length(@)`, `sort_by(@, &Field)`, `max_by(@, &Field)`, `to_string(@)`.

## Date-range filtering

Timestamps come back as ISO-8601 strings; JMESPath compares them
lexicographically, which is correct for ISO-8601:

```bash
# CloudFormation stacks created on/after a cutoff (string compare works for ISO-8601)
aws cloudformation list-stacks \
  --query "StackSummaries[?CreationTime>='2024-01-01'].StackName" \
  --output text
```

For true date math, prefer post-processing in `jq` or the calling shell rather
than JMESPath, which has no date arithmetic.

## `--output text` column ordering & scripting

- `--output text` emits **tab-separated** columns in the order given by a
  multi-select **list** (`[a,b,c]`); a multi-select **hash** (`{X:a,Y:b}`) sorts
  columns by key name — so use the list form when column order matters in a
  pipeline.
- Flatten to one value per line for `for`/`xargs` loops by querying a single
  field projection:

```bash
for id in $(aws ec2 describe-instances \
    --query 'Reservations[].Instances[].InstanceId' --output text); do
  echo "$id"
done
```

- Guard against empty results: an empty query yields an empty string in `text`
  output (not an error), so `[ -n "$out" ]` before iterating.

## `--output table` for humans

Use a multi-select hash so the header row is meaningful:

```bash
aws s3api list-buckets \
  --query 'Buckets[].{Name:Name,Created:CreationDate}' --output table
```

## Tips

- `--query` is client-side; for large result sets combine server-side
  `--filters` (where the API supports them) with `--query` to minimize transfer.
- Test a query incrementally with `--output json` first, then switch to
  `text`/`table` once the shape is right.
- Reserved-character keys (e.g. dashes) need quoting: `"some-key"`.
