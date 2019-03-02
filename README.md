# dynamo-item-updater

# dynamodb-item-updater

The application handles the pagination and coordinating the process across potentially many sequential executions of the Lambda. This application is useful if the size of the DynamoDB Table prevents a user from being able to Scan the entire Table within the execution time of a single Lambda (currently 15 min).

Made with ❤️ by Richard Boyd. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

## License

BSD with attribution (undefined)